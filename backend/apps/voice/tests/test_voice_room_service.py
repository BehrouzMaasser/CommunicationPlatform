from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.exceptions import (
    VoiceRoomMembershipRequired,
    VoiceRoomNameRequired,
    VoiceRoomNotFound,
    VoiceRoomOwnerCannotBeRemoved,
    VoiceRoomOwnerCannotLeave,
    VoiceRoomOwnerRequired,
)
from apps.voice.models import (
    VoiceRoom,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


class VoiceRoomServiceTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="room-owner",
            email="room-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="room-member",
            email="room-member@example.com",
            password=self.PASSWORD,
        )

        self.other_user = User.objects.create_user(
            username="room-other",
            email="room-other@example.com",
            password=self.PASSWORD,
        )

    def create_room(self):
        return VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def test_create_room_creates_owner_membership_atomically(self):
        room = self.create_room()

        self.assertEqual(
            room.owner,
            self.owner,
        )

        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=room,
                user=self.owner,
            ).exists()
        )

    def test_create_room_strips_name(self):
        room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="  Gaming  ",
        )

        self.assertEqual(
            room.name,
            "Gaming",
        )

    def test_create_room_rejects_empty_name(self):
        with self.assertRaises(
            VoiceRoomNameRequired
        ):
            VoiceRoomService.create_room(
                current_user=self.owner,
                name="   ",
            )

    def test_owner_can_rename_room(self):
        room = self.create_room()

        renamed = VoiceRoomService.rename_room(
            current_user=self.owner,
            room_id=room.id,
            name="Study",
        )

        self.assertEqual(
            renamed.name,
            "Study",
        )

    def test_non_owner_cannot_rename_room(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            VoiceRoomService.rename_room(
                current_user=self.member,
                room_id=room.id,
                name="Nope",
            )

    def test_member_can_leave_room(self):
        room = self.create_room()

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        VoiceRoomService.leave_room(
            current_user=self.member,
            room_id=room.id,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=room,
                user=self.member,
            ).exists()
        )

        self.assertTrue(
            VoiceRoom.objects.filter(
                pk=room.id,
            ).exists()
        )

    def test_owner_cannot_leave_room(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomOwnerCannotLeave
        ):
            VoiceRoomService.leave_room(
                current_user=self.owner,
                room_id=room.id,
            )

    def test_non_member_cannot_leave_room(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomMembershipRequired
        ):
            VoiceRoomService.leave_room(
                current_user=self.member,
                room_id=room.id,
            )

    def test_owner_can_remove_member(self):
        room = self.create_room()

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        VoiceRoomService.remove_member(
            current_user=self.owner,
            room_id=room.id,
            target_user=self.member,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=room,
                user=self.member,
            ).exists()
        )

    def test_non_owner_cannot_remove_member(self):
        room = self.create_room()

        VoiceRoomMembership.objects.create(
            room=room,
            user=self.member,
        )

        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            VoiceRoomService.remove_member(
                current_user=self.member,
                room_id=room.id,
                target_user=self.owner,
            )

    def test_owner_cannot_remove_themselves(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomOwnerCannotBeRemoved
        ):
            VoiceRoomService.remove_member(
                current_user=self.owner,
                room_id=room.id,
                target_user=self.owner,
            )

    def test_removing_non_member_fails(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomMembershipRequired
        ):
            VoiceRoomService.remove_member(
                current_user=self.owner,
                room_id=room.id,
                target_user=self.member,
            )

    def test_owner_can_delete_room(self):
        room = self.create_room()
        room_id = room.id

        VoiceRoomService.delete_room(
            current_user=self.owner,
            room_id=room_id,
        )

        self.assertFalse(
            VoiceRoom.objects.filter(
                pk=room_id,
            ).exists()
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room_id=room_id,
            ).exists()
        )

    def test_non_owner_cannot_delete_room(self):
        room = self.create_room()

        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            VoiceRoomService.delete_room(
                current_user=self.member,
                room_id=room.id,
            )

    def test_missing_room_raises_domain_error(self):
        room = self.create_room()
        room_id = room.id

        room.delete()

        with self.assertRaises(
            VoiceRoomNotFound
        ):
            VoiceRoomService.rename_room(
                current_user=self.owner,
                room_id=room_id,
                name="Missing",
            )
