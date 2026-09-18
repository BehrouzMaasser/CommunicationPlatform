import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.friendships.models import Friendship
from apps.voice.exceptions import (
    VoiceParticipationClaimed,
    VoiceParticipationNotActive,
    VoiceRoomMembershipRequired,
    VoiceUserBusy,
)
from apps.voice.models import (
    VoiceParticipation,
    VoiceRoomMembership,
    VoiceSession,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_session import (
    VoiceSessionService,
)


User = get_user_model()


class VoiceRoomSessionServiceTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            username="room-voice-alice",
            email="room-voice-alice@example.com",
            password=self.PASSWORD,
        )
        self.bob = User.objects.create_user(
            username="room-voice-bob",
            email="room-voice-bob@example.com",
            password=self.PASSWORD,
        )
        self.charlie = User.objects.create_user(
            username="room-voice-charlie",
            email="room-voice-charlie@example.com",
            password=self.PASSWORD,
        )

        self.alice_client = uuid.uuid4()
        self.bob_client = uuid.uuid4()

        self.room = VoiceRoomService.create_room(
            current_user=self.alice,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.bob,
        )

    @staticmethod
    def make_friends(user_a, user_b):
        user_1_id, user_2_id = sorted(
            (
                user_a.pk,
                user_b.pk,
            )
        )

        return Friendship.objects.create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

    def test_join_requires_room_membership(self):
        with self.assertRaises(
            VoiceRoomMembershipRequired
        ):
            VoiceSessionService.join_voice_room(
                current_user=self.charlie,
                room_id=self.room.id,
                client_instance_id=uuid.uuid4(),
            )

    def test_members_share_one_active_room_session(self):
        alice = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        bob = (
            VoiceSessionService.join_voice_room(
                current_user=self.bob,
                room_id=self.room.id,
                client_instance_id=self.bob_client,
            )
        )

        self.assertEqual(
            alice.session_id,
            bob.session_id,
        )

        session = alice.session

        self.assertEqual(
            session.kind,
            VoiceSession.Kind.ROOM,
        )

        self.assertEqual(
            session.voice_room_id,
            self.room.id,
        )

        self.assertEqual(
            VoiceSession.objects.filter(
                kind=VoiceSession.Kind.ROOM,
                voice_room=self.room,
                status=VoiceSession.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_join_is_idempotent_for_same_client(self):
        first = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        second = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        self.assertEqual(
            first.pk,
            second.pk,
        )

        with self.assertRaises(
            VoiceParticipationClaimed
        ):
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=uuid.uuid4(),
            )

    def test_direct_call_blocks_room_join(self):
        self.make_friends(
            self.alice,
            self.charlie,
        )

        VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.charlie.pk,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(
            VoiceUserBusy
        ):
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )

    def test_last_participant_leaving_ends_media_session(self):
        participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        VoiceSessionService.leave_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )

        participation.refresh_from_db()
        participation.session.refresh_from_db()

        self.assertIsNotNone(
            participation.left_at
        )

        self.assertEqual(
            participation.session.status,
            VoiceSession.Status.ENDED,
        )

        self.assertEqual(
            participation.session.end_reason,
            VoiceSession.EndReason.EMPTY,
        )

        # Persistent room membership remains.
        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.alice,
            ).exists()
        )

    def test_room_stays_active_while_other_participant_remains(
        self,
    ):
        alice = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        bob = (
            VoiceSessionService.join_voice_room(
                current_user=self.bob,
                room_id=self.room.id,
                client_instance_id=self.bob_client,
            )
        )

        VoiceSessionService.leave_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )

        alice.session.refresh_from_db()
        bob.refresh_from_db()

        self.assertEqual(
            alice.session.status,
            VoiceSession.Status.ACTIVE,
        )

        self.assertIsNone(
            bob.left_at
        )

    def test_member_can_rejoin_same_active_session_after_leaving(
        self,
    ):
        alice = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
        )

        first_bob = (
            VoiceSessionService.join_voice_room(
                current_user=self.bob,
                room_id=self.room.id,
                client_instance_id=self.bob_client,
            )
        )

        VoiceSessionService.leave_voice_room(
            current_user=self.bob,
            room_id=self.room.id,
            client_instance_id=self.bob_client,
        )

        first_bob.refresh_from_db()
        alice.session.refresh_from_db()

        self.assertIsNotNone(
            first_bob.left_at
        )
        self.assertEqual(
            alice.session.status,
            VoiceSession.Status.ACTIVE,
        )

        second_bob = (
            VoiceSessionService.join_voice_room(
                current_user=self.bob,
                room_id=self.room.id,
                client_instance_id=self.bob_client,
            )
        )

        self.assertEqual(
            second_bob.session_id,
            first_bob.session_id,
        )
        self.assertNotEqual(
            second_bob.pk,
            first_bob.pk,
        )
        self.assertIsNone(
            second_bob.left_at
        )

        self.assertEqual(
            VoiceParticipation.objects.filter(
                session_id=first_bob.session_id,
                user=self.bob,
            ).count(),
            2,
        )

        self.assertEqual(
            VoiceParticipation.objects.filter(
                user=self.bob,
                left_at__isnull=True,
            ).count(),
            1,
        )


    def test_active_participation_heartbeat_renews_ownership_lease(
        self,
    ):
        participation = VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )
        old_claim = timezone.now() - timedelta(minutes=5)
        VoiceParticipation.objects.filter(pk=participation.pk).update(
            claimed_at=old_claim,
        )

        VoiceSessionService.heartbeat_current_participation(
            current_user=self.alice,
            client_instance_id=self.alice_client,
        )

        participation.refresh_from_db()
        self.assertGreater(
            participation.claimed_at,
            old_claim,
        )

    @override_settings(VOICE_MEDIA_RECONCILE_GRACE_SECONDS=30)
    @patch(
        "apps.voice.services.voice_session.LiveKitMediaAdminService.list_participant_identities"
    )
    def test_heartbeat_reconciles_peer_with_expired_missing_lease(
        self, list_identities
    ):
        alice = VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )
        bob = VoiceSessionService.join_voice_room(
            current_user=self.bob,
            room_id=self.room.id,
            client_instance_id=self.bob_client,
        )
        VoiceParticipation.objects.filter(pk=bob.pk).update(
            claimed_at=timezone.now() - timedelta(minutes=5),
        )
        list_identities.return_value = {
            alice.media_participant_identity,
        }

        VoiceSessionService.heartbeat_current_participation(
            current_user=self.alice,
            client_instance_id=self.alice_client,
        )

        bob.refresh_from_db()
        self.assertIsNotNone(bob.left_at)

    def test_active_participation_heartbeat_rejects_other_client(
        self,
    ):
        VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(VoiceParticipationClaimed):
            VoiceSessionService.heartbeat_current_participation(
                current_user=self.alice,
                client_instance_id=uuid.uuid4(),
            )

    @override_settings(VOICE_MEDIA_RECONCILE_GRACE_SECONDS=30)
    @patch(
        "apps.voice.services.voice_session.LiveKitMediaAdminService.list_participant_identities"
    )
    def test_room_reconciliation_does_not_probe_fresh_voice_lease(
        self, list_identities
    ):
        VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )

        VoiceSessionService.reconcile_voice_room_media(
            room_id=self.room.id,
        )

        list_identities.assert_not_called()

    @patch(
        "apps.voice.services.voice_session.VoiceMediaCleanup.remove_participant_after_commit"
    )
    def test_active_participation_can_be_taken_over_by_new_client(
        self, remove_participant
    ):
        participation = VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )
        replacement_client = uuid.uuid4()

        result = VoiceSessionService.take_over_current_participation(
            current_user=self.alice,
            client_instance_id=replacement_client,
        )

        result.refresh_from_db()
        self.assertEqual(result.pk, participation.pk)
        self.assertEqual(
            result.client_instance_id,
            replacement_client,
        )
        remove_participant.assert_called_once_with(
            room_name=result.session.media_room_name,
            participant_identity=result.media_participant_identity,
        )

    @patch(
        "apps.voice.services.voice_session.VoiceMediaCleanup.remove_participant_after_commit"
    )
    def test_release_current_participation_works_from_other_client(
        self, remove_participant
    ):
        alice = VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )
        VoiceSessionService.join_voice_room(
            current_user=self.bob,
            room_id=self.room.id,
            client_instance_id=self.bob_client,
        )

        VoiceSessionService.release_current_participation(
            current_user=self.alice,
        )

        alice.refresh_from_db()
        alice.session.refresh_from_db()
        self.assertIsNotNone(alice.left_at)
        self.assertEqual(
            alice.session.status,
            VoiceSession.Status.ACTIVE,
        )
        remove_participant.assert_called_once()

    @override_settings(VOICE_MEDIA_RECONCILE_GRACE_SECONDS=0)
    @patch(
        "apps.voice.services.voice_session.LiveKitMediaAdminService.list_participant_identities"
    )
    def test_room_reconciliation_removes_media_ghosts(
        self, list_identities
    ):
        alice = VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )
        bob = VoiceSessionService.join_voice_room(
            current_user=self.bob,
            room_id=self.room.id,
            client_instance_id=self.bob_client,
        )
        list_identities.return_value = {
            alice.media_participant_identity
        }

        VoiceSessionService.reconcile_voice_room_media(
            room_id=self.room.id,
        )

        alice.refresh_from_db()
        bob.refresh_from_db()
        alice.session.refresh_from_db()

        self.assertIsNone(alice.left_at)
        self.assertIsNotNone(bob.left_at)
        self.assertEqual(
            alice.session.status,
            VoiceSession.Status.ACTIVE,
        )

    def test_wrong_client_cannot_leave_room_voice(self):
        VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=self.alice_client,
        )

        with self.assertRaises(
            VoiceParticipationClaimed
        ):
            VoiceSessionService.leave_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=uuid.uuid4(),
            )

    def test_leave_without_active_participation_is_rejected(
        self,
    ):
        with self.assertRaises(
            VoiceParticipationNotActive
        ):
            VoiceSessionService.leave_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=self.alice_client,
            )
