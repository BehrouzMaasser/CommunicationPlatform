import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.voice.models import (
    VoiceRoomMembership,
    VoiceSession,
)
from apps.voice.services.media import (
    VoiceMediaCredentials,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


@override_settings(
    VOICE_ENABLED=True
)
class VoiceRoomVoiceApiTests(APITestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            username="room-api-alice",
            email="room-api-alice@example.com",
            password=self.PASSWORD,
        )

        self.bob = User.objects.create_user(
            username="room-api-bob",
            email="room-api-bob@example.com",
            password=self.PASSWORD,
        )

        self.outsider = User.objects.create_user(
            username="room-api-outsider",
            email="room-api-outsider@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.alice,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.bob,
        )

        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()

    def authenticate(self, user):
        self.client.force_authenticate(
            user=user
        )

    def join(
        self,
        *,
        user,
        client_instance_id,
    ):
        self.authenticate(user)

        return self.client.post(
            reverse(
                "voice-room-voice",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "client_instance_id": str(
                    client_instance_id
                ),
            },
            format="json",
        )

    def test_member_can_join_room_voice(self):
        response = self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["kind"],
            "ROOM",
        )

        self.assertEqual(
            response.data["session"]["voice_room_id"],
            str(self.room.id),
        )

        self.assertIsNone(
            response.data["session"]["group_id"]
        )

        self.assertEqual(
            response.data["session"]["status"],
            "ACTIVE",
        )

        self.assertEqual(
            response.data[
                "current_participation"
            ]["client_instance_id"],
            str(self.alice_client),
        )

        self.assertEqual(
            len(response.data["participants"]),
            1,
        )

    def test_two_members_join_same_session(self):
        alice = self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        bob = self.join(
            user=self.bob,
            client_instance_id=self.bob_client,
        )

        self.assertEqual(
            alice.data["session"]["id"],
            bob.data["session"]["id"],
        )

        self.assertEqual(
            len(bob.data["participants"]),
            2,
        )

        self.assertEqual(
            VoiceSession.objects.filter(
                kind=VoiceSession.Kind.ROOM,
                voice_room=self.room,
                status=VoiceSession.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_member_can_get_current_room_voice_state(
        self,
    ):
        joined = self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        self.authenticate(
            self.alice
        )

        response = self.client.get(
            reverse(
                "voice-room-voice",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["id"],
            joined.data["session"]["id"],
        )

        self.assertEqual(
            len(response.data["participants"]),
            1,
        )

    def test_empty_room_has_no_active_media_session(
        self,
    ):
        self.authenticate(
            self.alice
        )

        response = self.client.get(
            reverse(
                "voice-room-voice",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIsNone(
            response.data["session"]
        )

        self.assertEqual(
            response.data["participants"],
            [],
        )

    def test_outsider_cannot_get_room_voice_state(
        self,
    ):
        self.authenticate(
            self.outsider
        )

        response = self.client.get(
            reverse(
                "voice-room-voice",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_outsider_cannot_join_room_voice(
        self,
    ):
        response = self.join(
            user=self.outsider,
            client_instance_id=uuid.uuid4(),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_leave_preserves_other_participant(
        self,
    ):
        self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        self.join(
            user=self.bob,
            client_instance_id=self.bob_client,
        )

        self.authenticate(
            self.bob
        )

        response = self.client.post(
            reverse(
                "voice-room-voice-leave",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "client_instance_id": str(
                    self.bob_client
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["status"],
            "ACTIVE",
        )

        self.assertIsNone(
            response.data[
                "current_participation"
            ]
        )

        self.assertEqual(
            len(response.data["participants"]),
            1,
        )

        self.assertEqual(
            response.data[
                "participants"
            ][0]["user"]["id"],
            self.alice.pk,
        )

    def test_last_leave_ends_media_session_but_room_remains(
        self,
    ):
        self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        self.authenticate(
            self.alice
        )

        response = self.client.post(
            reverse(
                "voice-room-voice-leave",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "client_instance_id": str(
                    self.alice_client
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["session"]["status"],
            "ENDED",
        )

        self.assertEqual(
            response.data["session"]["end_reason"],
            "EMPTY",
        )

        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.alice,
            ).exists()
        )

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_room_participant_can_get_media_credentials(
        self,
        issue,
    ):
        issue.return_value = VoiceMediaCredentials(
            server_url="wss://voice.example.test",
            participant_token="room-token",
        )

        joined = self.join(
            user=self.alice,
            client_instance_id=self.alice_client,
        )

        session_id = (
            joined.data["session"]["id"]
        )

        response = self.client.post(
            reverse(
                "voice-media-credentials",
                kwargs={
                    "session_id": session_id,
                },
            ),
            {
                "client_instance_id": str(
                    self.alice_client
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["server_url"],
            "wss://voice.example.test",
        )

        self.assertEqual(
            response.data["participant_token"],
            "room-token",
        )

        issue.assert_called_once()

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_removed_membership_blocks_new_media_credentials(
        self,
        issue,
    ):
        joined = self.join(
            user=self.bob,
            client_instance_id=self.bob_client,
        )

        session_id = (
            joined.data["session"]["id"]
        )

        # Simulate stale application state defensively:
        # membership is gone while participation still exists.
        VoiceRoomMembership.objects.filter(
            room=self.room,
            user=self.bob,
        ).delete()

        self.authenticate(
            self.bob
        )

        response = self.client.post(
            reverse(
                "voice-media-credentials",
                kwargs={
                    "session_id": session_id,
                },
            ),
            {
                "client_instance_id": str(
                    self.bob_client
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        issue.assert_not_called()
