from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


class VoiceRoomRealtimeIntegrationTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="room-rt-owner",
            email="room-rt-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="room-rt-member",
            email="room-rt-member@example.com",
            password=self.PASSWORD,
        )

    @patch(
        "apps.voice.services.voice_room."
        "VoiceRoomRealtimePublisher."
        "room_created_after_commit"
    )
    def test_create_room_publishes_created(
        self,
        publish,
    ):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        publish.assert_called_once_with(
            room_id=room.pk,
            room_name="Gaming",
            owner_id=self.owner.pk,
        )

    @patch(
        "apps.voice.services.voice_room."
        "VoiceRoomRealtimePublisher."
        "room_renamed_after_commit"
    )
    def test_rename_notifies_all_members(
        self,
        publish,
    ):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        VoiceRoomService.rename_room(
            current_user=self.owner,
            room_id=room.pk,
            name="Gaming 2",
        )

        publish.assert_called_once()

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["room_id"],
            room.pk,
        )

        self.assertEqual(
            kwargs["room_name"],
            "Gaming 2",
        )

        self.assertEqual(
            kwargs["audience_user_ids"],
            sorted(
                [
                    self.owner.pk,
                    self.member.pk,
                ]
            ),
        )

    @patch(
        "apps.voice.services.voice_room."
        "VoiceRoomRealtimePublisher."
        "member_left_after_commit"
    )
    def test_leave_notifies_remaining_member_and_leaver(
        self,
        publish,
    ):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        VoiceRoomService.leave_room(
            current_user=self.member,
            room_id=room.pk,
        )

        publish.assert_called_once_with(
            room_id=room.pk,
            member_user_id=self.member.pk,
            audience_user_ids=sorted(
                [
                    self.owner.pk,
                    self.member.pk,
                ]
            ),
        )

    @patch(
        "apps.voice.services.voice_room."
        "VoiceRoomRealtimePublisher."
        "member_removed_after_commit"
    )
    def test_remove_notifies_room_and_removed_member(
        self,
        publish,
    ):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        VoiceRoomService.remove_member(
            current_user=self.owner,
            room_id=room.pk,
            target_user=self.member,
        )

        publish.assert_called_once_with(
            room_id=room.pk,
            member_user_id=self.member.pk,
            audience_user_ids=sorted(
                [
                    self.owner.pk,
                    self.member.pk,
                ]
            ),
        )

    @patch(
        "apps.voice.services.voice_room."
        "VoiceRoomRealtimePublisher."
        "room_deleted_after_commit"
    )
    def test_delete_notifies_all_previous_members(
        self,
        publish,
    ):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        room_id = room.pk

        VoiceRoomService.delete_room(
            current_user=self.owner,
            room_id=room_id,
        )

        publish.assert_called_once_with(
            room_id=room_id,
            audience_user_ids=sorted(
                [
                    self.owner.pk,
                    self.member.pk,
                ]
            ),
        )
