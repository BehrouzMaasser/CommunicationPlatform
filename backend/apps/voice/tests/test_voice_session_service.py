import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import GroupConversation, GroupMembership
from apps.conversations.services.group_conversation import GroupConversationService
from apps.friendships.models import Friendship
from apps.voice.exceptions import (
    SelfVoiceCallNotAllowed,
    VoiceCallPermissionDenied,
    VoiceFriendshipRequired,
    VoiceGroupMembershipRequired,
    VoiceInvalidState,
    VoiceParticipationClaimed,
    VoiceParticipationNotActive,
    VoiceTargetUserNotFound,
    VoiceUserBusy,
)
from apps.voice.models import VoiceParticipation, VoiceSession
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


class VoiceSessionServiceTests(TestCase):
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
        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password=self.PASSWORD,
        )
        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()
        self.charlie_client = uuid.uuid4()

    @staticmethod
    def _make_friends(user_a, user_b):
        user_1_id, user_2_id = sorted((user_a.pk, user_b.pk))
        return Friendship.objects.create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

    def _create_group_with_members(self, *users):
        group = GroupConversation.objects.create(
            name="Voice Group",
        )
        for index, user in enumerate(users):
            GroupMembership.objects.create(
                group=group,
                user=user,
                role=(
                    GroupMembership.Role.OWNER
                    if index == 0
                    else GroupMembership.Role.MEMBER
                ),
            )
        return group

    def test_start_direct_call_requires_friendship(self):
        with self.assertRaises(VoiceFriendshipRequired):
            VoiceSessionService.start_direct_call(
                current_user=self.alice,
                target_user_id=self.bob.pk,
                client_instance_id=self.alice_client,
            )

        self.assertFalse(VoiceSession.objects.exists())

    def test_start_direct_call_rejects_self(self):
        with self.assertRaises(SelfVoiceCallNotAllowed):
            VoiceSessionService.start_direct_call(
                current_user=self.alice,
                target_user_id=self.alice.pk,
                client_instance_id=self.alice_client,
            )

    def test_start_direct_call_rejects_unknown_target(self):
        with self.assertRaises(VoiceTargetUserNotFound):
            VoiceSessionService.start_direct_call(
                current_user=self.alice,
                target_user_id=999999,
                client_instance_id=self.alice_client,
            )

    def test_start_direct_call_reserves_both_accounts(self):
        self._make_friends(self.alice, self.bob)

        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        self.assertEqual(session.status, VoiceSession.Status.RINGING)
        self.assertIsNone(session.activated_at)
        self.assertIsNotNone(session.ring_expires_at)
        self.assertGreater(session.ring_expires_at, timezone.now())

        caller = VoiceParticipation.objects.get(
            session=session,
            user=self.alice,
        )
        callee = VoiceParticipation.objects.get(
            session=session,
            user=self.bob,
        )

        self.assertEqual(caller.role, VoiceParticipation.Role.CALLER)
        self.assertEqual(caller.client_instance_id, self.alice_client)
        self.assertIsNotNone(caller.claimed_at)
        self.assertEqual(callee.role, VoiceParticipation.Role.CALLEE)
        self.assertIsNone(callee.client_instance_id)
        self.assertIsNone(callee.claimed_at)
        self.assertIsNone(caller.left_at)
        self.assertIsNone(callee.left_at)

    def test_expired_ringing_call_is_lazily_released_before_new_call(self):
        self._make_friends(self.alice, self.bob)
        self._make_friends(self.alice, self.charlie)

        expired = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )
        VoiceSession.objects.filter(pk=expired.pk).update(
            ring_expires_at=timezone.now() - timedelta(seconds=1)
        )

        new_session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.charlie.pk,
            client_instance_id=self.alice_client,
        )

        expired.refresh_from_db()
        self.assertEqual(expired.status, VoiceSession.Status.ENDED)
        self.assertEqual(expired.end_reason, VoiceSession.EndReason.MISSED)
        self.assertEqual(new_session.status, VoiceSession.Status.RINGING)

    def test_expired_ringing_call_cannot_be_accepted_and_becomes_missed(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )
        VoiceSession.objects.filter(pk=session.pk).update(
            ring_expires_at=timezone.now() - timedelta(seconds=1)
        )

        with self.assertRaises(VoiceInvalidState):
            VoiceSessionService.accept_direct_call(
                current_user=self.bob,
                session_id=session.pk,
                client_instance_id=self.bob_client,
            )

        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.MISSED)

    def test_direct_call_rejects_busy_target(self):
        self._make_friends(self.alice, self.bob)
        self._make_friends(self.charlie, self.bob)

        VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceUserBusy):
            VoiceSessionService.start_direct_call(
                current_user=self.charlie,
                target_user_id=self.bob.pk,
                client_instance_id=self.charlie_client,
            )

    def test_recipient_accepts_and_first_client_instance_wins(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        accepted = VoiceSessionService.accept_direct_call(
            current_user=self.bob,
            session_id=session.pk,
            client_instance_id=self.bob_client,
        )

        self.assertEqual(accepted.status, VoiceSession.Status.ACTIVE)
        self.assertIsNotNone(accepted.activated_at)

        bob_participation = VoiceParticipation.objects.get(
            session=session,
            user=self.bob,
        )
        self.assertEqual(
            bob_participation.client_instance_id,
            self.bob_client,
        )

        same_device_retry = VoiceSessionService.accept_direct_call(
            current_user=self.bob,
            session_id=session.pk,
            client_instance_id=self.bob_client,
        )
        self.assertEqual(same_device_retry.pk, session.pk)

        with self.assertRaises(VoiceParticipationClaimed):
            VoiceSessionService.accept_direct_call(
                current_user=self.bob,
                session_id=session.pk,
                client_instance_id=uuid.uuid4(),
            )

    def test_only_recipient_can_accept_direct_call(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceCallPermissionDenied):
            VoiceSessionService.accept_direct_call(
                current_user=self.alice,
                session_id=session.pk,
                client_instance_id=self.alice_client,
            )

    def test_reject_closes_both_participations(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        VoiceSessionService.reject_direct_call(
            current_user=self.bob,
            session_id=session.pk,
        )

        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.REJECTED)
        self.assertIsNotNone(session.ended_at)
        self.assertFalse(
            VoiceParticipation.objects.filter(
                session=session,
                left_at__isnull=True,
            ).exists()
        )

    def test_ringing_call_can_be_marked_missed(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        VoiceSession.objects.filter(pk=session.pk).update(
            ring_expires_at=timezone.now() - timedelta(seconds=1)
        )

        VoiceSessionService.mark_direct_call_missed(
            session_id=session.pk,
        )

        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.MISSED)

    def test_caller_can_cancel_ringing_call(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        VoiceSessionService.cancel_direct_call(
            current_user=self.alice,
            session_id=session.pk,
        )

        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.CANCELLED)

    def test_active_direct_call_can_be_ended_by_participant(self):
        self._make_friends(self.alice, self.bob)
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

        session.refresh_from_db()
        self.assertEqual(session.status, VoiceSession.Status.ENDED)
        self.assertEqual(session.end_reason, VoiceSession.EndReason.HANGUP)

    def test_cannot_end_direct_call_while_ringing(self):
        self._make_friends(self.alice, self.bob)
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceInvalidState):
            VoiceSessionService.end_direct_call(
                current_user=self.alice,
                session_id=session.pk,
            )

    def test_group_join_requires_current_membership(self):
        group = self._create_group_with_members(self.alice)

        with self.assertRaises(VoiceGroupMembershipRequired):
            VoiceSessionService.join_group_voice(
                current_user=self.bob,
                group_id=group.pk,
                client_instance_id=self.bob_client,
            )

    def test_group_members_share_one_active_session(self):
        group = self._create_group_with_members(self.alice, self.bob)

        alice_participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )
        bob_participation = VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=group.pk,
            client_instance_id=self.bob_client,
        )

        self.assertEqual(
            alice_participation.session_id,
            bob_participation.session_id,
        )
        self.assertEqual(
            VoiceSession.objects.filter(
                group=group,
                status=VoiceSession.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_group_join_is_idempotent_for_same_client_instance(self):
        group = self._create_group_with_members(self.alice)

        first = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )
        second = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        self.assertEqual(first.pk, second.pk)

        with self.assertRaises(VoiceParticipationClaimed):
            VoiceSessionService.join_group_voice(
                current_user=self.alice,
                group_id=group.pk,
                client_instance_id=uuid.uuid4(),
            )

    def test_direct_ringing_call_blocks_group_join(self):
        self._make_friends(self.alice, self.bob)
        group = self._create_group_with_members(self.alice)

        VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceUserBusy):
            VoiceSessionService.join_group_voice(
                current_user=self.alice,
                group_id=group.pk,
                client_instance_id=self.alice_client,
            )

    def test_last_group_participant_leaving_ends_room(self):
        group = self._create_group_with_members(self.alice)
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

        participation.refresh_from_db()
        participation.session.refresh_from_db()
        self.assertIsNotNone(participation.left_at)
        self.assertEqual(
            participation.session.status,
            VoiceSession.Status.ENDED,
        )
        self.assertEqual(
            participation.session.end_reason,
            VoiceSession.EndReason.EMPTY,
        )

    def test_group_room_stays_active_while_another_participant_remains(self):
        group = self._create_group_with_members(self.alice, self.bob)
        alice_participation = VoiceSessionService.join_group_voice(
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

        alice_participation.session.refresh_from_db()
        self.assertEqual(
            alice_participation.session.status,
            VoiceSession.Status.ACTIVE,
        )

    def test_wrong_client_cannot_leave_owned_group_participation(self):
        group = self._create_group_with_members(self.alice)
        VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceParticipationClaimed):
            VoiceSessionService.leave_group_voice(
                current_user=self.alice,
                group_id=group.pk,
                client_instance_id=uuid.uuid4(),
            )

    def test_group_member_removal_revokes_voice_participation(self):
        group = self._create_group_with_members(self.alice, self.bob)
        bob_participation = VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=group.pk,
            client_instance_id=self.bob_client,
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=group.pk,
            member_user_id=self.bob.pk,
        )

        bob_participation.refresh_from_db()
        self.assertIsNotNone(bob_participation.left_at)
        bob_participation.session.refresh_from_db()
        self.assertEqual(
            bob_participation.session.status,
            VoiceSession.Status.ENDED,
        )

    def test_group_member_leave_revokes_voice_participation(self):
        group = self._create_group_with_members(self.alice, self.bob)
        bob_participation = VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=group.pk,
            client_instance_id=self.bob_client,
        )

        GroupConversationService.leave_group(
            current_user=self.bob,
            group_id=group.pk,
        )

        bob_participation.refresh_from_db()
        self.assertIsNotNone(bob_participation.left_at)

    def test_group_disband_invalidates_voice_state(self):
        group = self._create_group_with_members(self.alice, self.bob)
        VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=group.pk,
            client_instance_id=self.alice_client,
        )
        session_id = VoiceSession.objects.get(
            group=group,
            status=VoiceSession.Status.ACTIVE,
        ).pk

        GroupConversationService.disband_group(
            current_user=self.alice,
            group_id=group.pk,
        )

        self.assertFalse(
            VoiceSession.objects.filter(pk=session_id).exists()
        )

    def test_client_instance_id_must_be_uuid(self):
        group = self._create_group_with_members(self.alice)

        with self.assertRaises(ValueError):
            VoiceSessionService.join_group_voice(
                current_user=self.alice,
                group_id=group.pk,
                client_instance_id="not-a-uuid",
            )

    def test_callee_cannot_reject_after_call_is_active(self):
        self._make_friends(self.alice, self.bob)
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

        with self.assertRaises(VoiceInvalidState):
            VoiceSessionService.reject_direct_call(
                current_user=self.bob,
                session_id=session.pk,
            )

    def test_leaving_nonexistent_group_participation_is_rejected(self):
        group = self._create_group_with_members(self.alice)

        with self.assertRaises(VoiceParticipationNotActive):
            VoiceSessionService.leave_group_voice(
                current_user=self.alice,
                group_id=group.pk,
                client_instance_id=self.alice_client,
            )
