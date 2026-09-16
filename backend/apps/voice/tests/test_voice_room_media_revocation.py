import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.models import (
    VoiceParticipation,
    VoiceRoom,
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


class VoiceRoomMediaRevocationTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="revoke-owner",
            email="revoke-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="revoke-member",
            email="revoke-member@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

        self.owner_client = uuid.uuid4()
        self.member_client = uuid.uuid4()

    def test_member_leaving_room_revokes_active_media(
        self,
    ):
        participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.member,
                room_id=self.room.id,
                client_instance_id=self.member_client,
            )
        )

        VoiceRoomService.leave_room(
            current_user=self.member,
            room_id=self.room.id,
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

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.member,
            ).exists()
        )

    def test_removing_member_revokes_only_that_participant(
        self,
    ):
        owner_participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.owner,
                room_id=self.room.id,
                client_instance_id=self.owner_client,
            )
        )

        member_participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.member,
                room_id=self.room.id,
                client_instance_id=self.member_client,
            )
        )

        VoiceRoomService.remove_member(
            current_user=self.owner,
            room_id=self.room.id,
            target_user=self.member,
        )

        owner_participation.refresh_from_db()
        member_participation.refresh_from_db()
        owner_participation.session.refresh_from_db()

        self.assertIsNone(
            owner_participation.left_at
        )

        self.assertIsNotNone(
            member_participation.left_at
        )

        self.assertEqual(
            owner_participation.session.status,
            VoiceSession.Status.ACTIVE,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.member,
            ).exists()
        )

    def test_removed_member_can_rejoin_media_after_being_added_back(
        self,
    ):
        owner_participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.owner,
                room_id=self.room.id,
                client_instance_id=self.owner_client,
            )
        )

        first_member_participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.member,
                room_id=self.room.id,
                client_instance_id=self.member_client,
            )
        )

        VoiceRoomService.remove_member(
            current_user=self.owner,
            room_id=self.room.id,
            target_user=self.member,
        )

        first_member_participation.refresh_from_db()
        owner_participation.session.refresh_from_db()

        self.assertIsNotNone(
            first_member_participation.left_at
        )
        self.assertEqual(
            owner_participation.session.status,
            VoiceSession.Status.ACTIVE,
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

        second_member_participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.member,
                room_id=self.room.id,
                client_instance_id=self.member_client,
            )
        )

        self.assertEqual(
            second_member_participation.session_id,
            owner_participation.session_id,
        )
        self.assertNotEqual(
            second_member_participation.pk,
            first_member_participation.pk,
        )
        self.assertIsNone(
            second_member_participation.left_at
        )

        self.assertEqual(
            VoiceParticipation.objects.filter(
                user=self.member,
                left_at__isnull=True,
            ).count(),
            1,
        )


    @patch(
        "apps.voice.services.voice_session."
        "VoiceRealtimePublisher."
        "room_session_ended_after_commit"
    )
    @patch(
        "apps.voice.services.voice_session."
        "VoiceMediaCleanup."
        "delete_room_after_commit"
    )
    def test_delete_room_revokes_whole_active_session(
        self,
        delete_media_room,
        publish_session_ended,
    ):
        participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.owner,
                room_id=self.room.id,
                client_instance_id=self.owner_client,
            )
        )

        session = participation.session
        session_id = session.pk
        media_room_name = (
            session.media_room_name
        )
        room_id = self.room.id

        VoiceRoomService.delete_room(
            current_user=self.owner,
            room_id=room_id,
        )

        self.assertFalse(
            VoiceRoom.objects.filter(
                pk=room_id,
            ).exists()
        )

        # VoiceSession.voice_room uses CASCADE, so deleting the persistent
        # room also removes its historical media-session row.
        self.assertFalse(
            VoiceSession.objects.filter(
                pk=session_id,
            ).exists()
        )

        delete_media_room.assert_called_once_with(
            room_name=media_room_name,
        )

        publish_session_ended.assert_called_once()

        kwargs = (
            publish_session_ended
            .call_args
            .kwargs
        )

        self.assertEqual(
            kwargs["session_id"],
            session_id,
        )

        self.assertEqual(
            kwargs["room_id"],
            room_id,
        )

        self.assertEqual(
            kwargs["end_reason"],
            VoiceSession.EndReason.ACCESS_REVOKED,
        )

        self.assertIn(
            self.owner.pk,
            kwargs["audience_user_ids"],
        )

    def test_membership_change_without_active_media_still_works(
        self,
    ):
        VoiceRoomService.remove_member(
            current_user=self.owner,
            room_id=self.room.id,
            target_user=self.member,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.member,
            ).exists()
        )

        self.assertFalse(
            VoiceParticipation.objects.filter(
                user=self.member,
                left_at__isnull=True,
            ).exists()
        )
