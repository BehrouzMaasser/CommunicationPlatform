import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.conversations.services.group_conversation import GroupConversationService
from apps.friendships.models import Friendship
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


class VoiceMediaCleanupIntegrationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice-media@example.com",
            username="alice-media",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            email="bob-media@example.com",
            username="bob-media",
            password="password-123",
        )
        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()

    def _make_friends(self):
        user_1, user_2 = sorted(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )
        Friendship.objects.create(user_1=user_1, user_2=user_2)

    def _group(self):
        group = GroupConversation.objects.create(name="Media cleanup group")
        GroupMembership.objects.create(
            group=group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        GroupMembership.objects.create(
            group=group,
            user=self.bob,
            role=GroupMembership.Role.MEMBER,
        )
        return group

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.delete_room_after_commit"
    )
    def test_direct_hangup_schedules_room_delete(self, delete_room):
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

        VoiceSessionService.end_direct_call(
            current_user=self.alice,
            session_id=session.pk,
        )

        delete_room.assert_called_once_with(
            room_name=session.media_room_name,
        )

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.delete_room_after_commit"
    )
    def test_repeated_direct_hangup_does_not_schedule_duplicate_cleanup(
        self,
        delete_room,
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

        VoiceSessionService.end_direct_call(
            current_user=self.alice,
            session_id=session.pk,
        )
        VoiceSessionService.end_direct_call(
            current_user=self.bob,
            session_id=session.pk,
        )

        delete_room.assert_called_once_with(
            room_name=session.media_room_name,
        )

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.remove_participant_after_commit"
    )
    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.delete_room_after_commit"
    )
    def test_group_leave_removes_only_departing_participant_when_room_remains(
        self,
        delete_room,
        remove_participant,
    ):
        group = self._group()
        alice = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )
        VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=group.pk,
            client_instance_id=self.bob_client,
        )

        VoiceSessionService.leave_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        remove_participant.assert_called_once_with(
            room_name=alice.session.media_room_name,
            participant_identity=alice.media_participant_identity,
        )
        delete_room.assert_not_called()

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.delete_room_after_commit"
    )
    def test_last_group_leave_schedules_room_delete(self, delete_room):
        group = self._group()
        participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        VoiceSessionService.leave_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        delete_room.assert_called_once_with(
            room_name=participation.session.media_room_name,
        )

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.remove_participant_after_commit"
    )
    def test_group_membership_revocation_schedules_media_removal(
        self,
        remove_participant,
    ):
        group = self._group()
        VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )
        bob = VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=group.pk,
            client_instance_id=self.bob_client,
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=group.pk,
            member_user_id=self.bob.pk,
        )

        remove_participant.assert_called_once_with(
            room_name=bob.session.media_room_name,
            participant_identity=bob.media_participant_identity,
        )

    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup.delete_room_after_commit"
    )
    def test_group_disband_schedules_room_delete(self, delete_room):
        group = self._group()
        participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        GroupConversationService.disband_group(
            current_user=self.alice,
            group_id=group.pk,
        )

        delete_room.assert_called_once_with(
            room_name=participation.session.media_room_name,
        )
