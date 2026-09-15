import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.friendships.models import Friendship
from apps.voice.models import VoiceSession
from apps.voice.services.media import VoiceMediaCredentials
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


@override_settings(VOICE_ENABLED=True)
class VoiceApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password-123",
        )
        self.charlie = User.objects.create_user(
            username="charlie",
            email="charlie@example.com",
            password="password-123",
        )

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )
        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.group = GroupConversation.objects.create(
            name="Study Group",
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=GroupMembership.Role.MEMBER,
        )

        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()
        self.bob_other_client = uuid.uuid4()

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def start_call(self):
        self.authenticate(self.alice)
        response = self.client.post(
            reverse("voice-direct-call-start"),
            {
                "user_id": self.bob.pk,
                "client_instance_id": str(self.alice_client),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response

    def test_anonymous_state_requires_authentication(self):
        response = self.client.get(reverse("voice-state"))
        self.assertEqual(response.status_code, 401)

    @override_settings(VOICE_ENABLED=False)
    def test_disabled_voice_does_not_create_call_state(self):
        self.authenticate(self.alice)
        response = self.client.post(
            reverse("voice-direct-call-start"),
            {
                "user_id": self.bob.pk,
                "client_instance_id": str(self.alice_client),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "VOICE_UNAVAILABLE")
        self.assertFalse(VoiceSession.objects.exists())

    def test_start_direct_call_returns_recoverable_state(self):
        response = self.start_call()

        self.assertEqual(response.data["session"]["kind"], "DIRECT")
        self.assertEqual(response.data["session"]["status"], "RINGING")
        self.assertEqual(
            response.data["session"]["caller"]["id"],
            self.alice.pk,
        )
        self.assertEqual(
            response.data["session"]["recipient"]["id"],
            self.bob.pk,
        )
        self.assertEqual(
            response.data["current_participation"]["client_instance_id"],
            str(self.alice_client),
        )
        self.assertEqual(len(response.data["participants"]), 2)

    def test_start_direct_call_requires_friendship(self):
        self.authenticate(self.alice)
        response = self.client.post(
            reverse("voice-direct-call-start"),
            {
                "user_id": self.charlie.pk,
                "client_instance_id": str(self.alice_client),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "VOICE_FRIENDSHIP_REQUIRED")

    def test_invalid_client_instance_id_is_payload_error(self):
        self.authenticate(self.alice)
        response = self.client.post(
            reverse("voice-direct-call-start"),
            {
                "user_id": self.bob.pk,
                "client_instance_id": "not-a-uuid",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("client_instance_id", response.data)

    def test_recipient_state_shows_unclaimed_ringing_participation(self):
        self.start_call()
        self.authenticate(self.bob)

        response = self.client.get(reverse("voice-state"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session"]["status"], "RINGING")
        self.assertEqual(
            response.data["current_participation"]["role"],
            "CALLEE",
        )
        self.assertIsNone(
            response.data["current_participation"]["client_instance_id"]
        )

    def test_accept_direct_call_claims_first_client(self):
        started = self.start_call()
        session_id = started.data["session"]["id"]
        self.authenticate(self.bob)

        accepted = self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data["session"]["status"], "ACTIVE")
        self.assertEqual(
            accepted.data["current_participation"]["client_instance_id"],
            str(self.bob_client),
        )

        other_device = self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_other_client)},
            format="json",
        )
        self.assertEqual(other_device.status_code, 409)
        self.assertEqual(
            other_device.data["code"],
            "VOICE_PARTICIPATION_CLAIMED",
        )

    def test_non_recipient_cannot_accept_call(self):
        started = self.start_call()
        self.authenticate(self.charlie)

        response = self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": started.data["session"]["id"]},
            ),
            {"client_instance_id": str(uuid.uuid4())},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "VOICE_SESSION_NOT_FOUND")

    def test_reject_direct_call_returns_ended_state(self):
        started = self.start_call()
        self.authenticate(self.bob)

        response = self.client.post(
            reverse(
                "voice-direct-call-reject",
                kwargs={"session_id": started.data["session"]["id"]},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session"]["status"], "ENDED")
        self.assertEqual(response.data["session"]["end_reason"], "REJECTED")
        self.assertIsNone(response.data["current_participation"])
        self.assertEqual(response.data["participants"], [])

    def test_caller_can_cancel_ringing_call(self):
        started = self.start_call()
        self.authenticate(self.alice)

        response = self.client.post(
            reverse(
                "voice-direct-call-cancel",
                kwargs={"session_id": started.data["session"]["id"]},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session"]["end_reason"], "CANCELLED")

    def test_active_direct_call_can_be_ended_by_participant(self):
        started = self.start_call()
        session_id = started.data["session"]["id"]
        self.authenticate(self.bob)
        self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        response = self.client.post(
            reverse(
                "voice-direct-call-end",
                kwargs={"session_id": session_id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session"]["end_reason"], "HANGUP")

    def test_state_reconciliation_expires_stale_ring(self):
        started = self.start_call()
        session = VoiceSession.objects.get(pk=started.data["session"]["id"])
        session.ring_expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["ring_expires_at"])

        self.authenticate(self.bob)
        response = self.client.get(reverse("voice-state"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["session"])
        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.MISSED)

    def test_group_voice_get_is_private_to_members(self):
        self.authenticate(self.charlie)
        response = self.client.get(
            reverse("group-voice", kwargs={"group_id": self.group.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_group_join_and_get_return_participants(self):
        self.authenticate(self.alice)
        joined = self.client.post(
            reverse("group-voice", kwargs={"group_id": self.group.pk}),
            {"client_instance_id": str(self.alice_client)},
            format="json",
        )

        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.data["session"]["kind"], "GROUP")
        self.assertEqual(len(joined.data["participants"]), 1)

        self.authenticate(self.bob)
        bob_joined = self.client.post(
            reverse("group-voice", kwargs={"group_id": self.group.pk}),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )
        self.assertEqual(bob_joined.status_code, 200)
        self.assertEqual(len(bob_joined.data["participants"]), 2)

        current = self.client.get(
            reverse("group-voice", kwargs={"group_id": self.group.pk})
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(len(current.data["participants"]), 2)

    def test_group_leave_preserves_other_participant(self):
        self.authenticate(self.alice)
        self.client.post(
            reverse("group-voice", kwargs={"group_id": self.group.pk}),
            {"client_instance_id": str(self.alice_client)},
            format="json",
        )
        self.authenticate(self.bob)
        self.client.post(
            reverse("group-voice", kwargs={"group_id": self.group.pk}),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        response = self.client.post(
            reverse(
                "group-voice-leave",
                kwargs={"group_id": self.group.pk},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session"]["status"], "ACTIVE")
        self.assertIsNone(response.data["current_participation"])
        self.assertEqual(len(response.data["participants"]), 1)
        self.assertEqual(
            response.data["participants"][0]["user"]["id"],
            self.alice.pk,
        )

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_media_credentials_require_owned_active_participation(self, issue):
        issue.return_value = VoiceMediaCredentials(
            server_url="wss://voice.example.test",
            participant_token="token-123",
        )

        started = self.start_call()
        session_id = started.data["session"]["id"]
        self.authenticate(self.bob)
        self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        response = self.client.post(
            reverse(
                "voice-media-credentials",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["server_url"], "wss://voice.example.test")
        self.assertEqual(response.data["participant_token"], "token-123")
        issue.assert_called_once()

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_media_credentials_reject_other_device(self, issue):
        started = self.start_call()
        session_id = started.data["session"]["id"]
        self.authenticate(self.bob)
        self.client.post(
            reverse(
                "voice-direct-call-accept",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        response = self.client.post(
            reverse(
                "voice-media-credentials",
                kwargs={"session_id": session_id},
            ),
            {"client_instance_id": str(self.bob_other_client)},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "VOICE_PARTICIPATION_CLAIMED")
        issue.assert_not_called()
