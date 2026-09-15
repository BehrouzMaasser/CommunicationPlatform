import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.friendships.models import Friendship
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


@override_settings(VOICE_ENABLED=True)
class VoiceRealtimeIntegrationTests(APITestCase):
    PUBLISH_PATH = (
        "apps.voice.realtime."
        "RealtimePublisher.publish_to_users_after_commit"
    )

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

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )
        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.group = GroupConversation.objects.create(name="Study Group")
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

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    @patch(PUBLISH_PATH)
    def test_start_call_publishes_ringing_to_both_accounts(self, publish):
        self.authenticate(self.alice)
        response = self.client.post(
            "/api/v1/voice/direct-calls/",
            {
                "user_id": self.bob.pk,
                "client_instance_id": str(self.alice_client),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        publish.assert_called_once()
        kwargs = publish.call_args.kwargs
        self.assertEqual(
            kwargs["event_type"].value,
            "voice.direct_call.ringing",
        )
        self.assertEqual(
            set(kwargs["user_ids"]),
            {self.alice.pk, self.bob.pk},
        )
        self.assertEqual(
            kwargs["payload"]["session_id"],
            response.data["session"]["id"],
        )

    @patch(PUBLISH_PATH)
    def test_accept_event_identifies_winning_client_instance(self, publish):
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )
        publish.reset_mock()

        self.authenticate(self.bob)
        response = self.client.post(
            f"/api/v1/voice/direct-calls/{session.pk}/accept/",
            {"client_instance_id": str(self.bob_client)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        publish.assert_called_once()
        kwargs = publish.call_args.kwargs
        self.assertEqual(
            kwargs["event_type"].value,
            "voice.direct_call.accepted",
        )
        self.assertEqual(
            kwargs["payload"]["accepted_by_client_instance_id"],
            str(self.bob_client),
        )

    @patch(PUBLISH_PATH)
    def test_group_join_publishes_to_all_group_members(self, publish):
        self.authenticate(self.alice)
        response = self.client.post(
            f"/api/v1/groups/{self.group.pk}/voice/",
            {"client_instance_id": str(self.alice_client)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        publish.assert_called_once()
        kwargs = publish.call_args.kwargs
        self.assertEqual(
            kwargs["event_type"].value,
            "voice.group.participant_joined",
        )
        self.assertEqual(
            set(kwargs["user_ids"]),
            {self.alice.pk, self.bob.pk},
        )
        self.assertEqual(kwargs["payload"]["group_id"], self.group.pk)
        self.assertEqual(kwargs["payload"]["user_id"], self.alice.pk)

    @patch(PUBLISH_PATH)
    def test_group_membership_removal_publishes_voice_revocation(self, publish):
        VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=self.group.pk,
            client_instance_id=self.bob_client,
        )
        publish.reset_mock()

        from apps.conversations.services.group_conversation import (
            GroupConversationService,
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        matching = [
            call.kwargs
            for call in publish.call_args_list
            if call.kwargs["event_type"].value
            == "voice.group.participant_revoked"
        ]
        self.assertEqual(len(matching), 1)
        self.assertIn(self.bob.pk, set(matching[0]["user_ids"]))
        self.assertEqual(matching[0]["payload"]["user_id"], self.bob.pk)
