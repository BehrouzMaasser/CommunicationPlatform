import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.friendships.models import Friendship
from apps.voice.exceptions import (
    VoiceGroupMembershipRequired,
    VoiceInvalidState,
    VoiceParticipationClaimed,
)
from apps.voice.services.media import VoiceMediaCredentials
from apps.voice.services.media_access import VoiceMediaAccessService
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


class VoiceMediaAccessServiceTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )
        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password=self.PASSWORD,
        )
        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()

    def _make_friends(self):
        user_1_id, user_2_id = sorted((self.alice.pk, self.bob.pk))
        Friendship.objects.create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_active_direct_participant_receives_opaque_media_identity(
        self,
        issue_join_credentials,
    ):
        issue_join_credentials.return_value = VoiceMediaCredentials(
            server_url="ws://livekit.test",
            participant_token="signed-token",
        )
        self._make_friends()
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )
        VoiceSessionService.accept_direct_call(
            current_user=self.bob,
            session_id=session.pk,
            client_instance_id=self.bob_client,
        )

        credentials = VoiceMediaAccessService.issue_credentials(
            current_user=self.alice,
            session_id=session.pk,
            client_instance_id=self.alice_client,
        )

        self.assertEqual(credentials.participant_token, "signed-token")
        kwargs = issue_join_credentials.call_args.kwargs
        self.assertEqual(kwargs["room_name"], session.media_room_name)
        self.assertNotIn(self.alice.username, kwargs["room_name"])
        self.assertNotIn(self.alice.email, kwargs["room_name"])
        self.assertTrue(
            kwargs["participant_identity"].startswith(
                "voice_participant_"
            )
        )
        self.assertNotIn(
            self.alice.username,
            kwargs["participant_identity"],
        )
        self.assertNotIn(
            self.alice.email,
            kwargs["participant_identity"],
        )

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_ringing_direct_call_cannot_receive_media_credentials(
        self,
        issue_join_credentials,
    ):
        self._make_friends()
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceInvalidState):
            VoiceMediaAccessService.issue_credentials(
                current_user=self.alice,
                session_id=session.pk,
                client_instance_id=self.alice_client,
            )

        issue_join_credentials.assert_not_called()

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_wrong_client_instance_cannot_receive_credentials(
        self,
        issue_join_credentials,
    ):
        self._make_friends()
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )
        VoiceSessionService.accept_direct_call(
            current_user=self.bob,
            session_id=session.pk,
            client_instance_id=self.bob_client,
        )

        with self.assertRaises(VoiceParticipationClaimed):
            VoiceMediaAccessService.issue_credentials(
                current_user=self.alice,
                session_id=session.pk,
                client_instance_id=uuid.uuid4(),
            )

        issue_join_credentials.assert_not_called()

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_current_group_member_can_receive_media_credentials(
        self,
        issue_join_credentials,
    ):
        issue_join_credentials.return_value = VoiceMediaCredentials(
            server_url="ws://livekit.test",
            participant_token="group-token",
        )
        group = GroupConversation.objects.create(name="Voice Group")
        GroupMembership.objects.create(
            group=group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        credentials = VoiceMediaAccessService.issue_credentials(
            current_user=self.alice,
            session_id=participation.session_id,
            client_instance_id=self.alice_client,
        )

        self.assertEqual(credentials.participant_token, "group-token")
        issue_join_credentials.assert_called_once()

    @patch(
        "apps.voice.services.media_access."
        "LiveKitMediaService.issue_join_credentials"
    )
    def test_group_media_access_rechecks_current_membership(
        self,
        issue_join_credentials,
    ):
        group = GroupConversation.objects.create(name="Voice Group")
        membership = GroupMembership.objects.create(
            group=group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        # Simulate a mutation that bypasses the group service. The credential
        # boundary still refuses stale authorization.
        membership.delete()

        with self.assertRaises(VoiceGroupMembershipRequired):
            VoiceMediaAccessService.issue_credentials(
                current_user=self.alice,
                session_id=participation.session_id,
                client_instance_id=self.alice_client,
            )

        issue_join_credentials.assert_not_called()
