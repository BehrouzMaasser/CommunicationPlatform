from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.selectors.voice_room import (
    VoiceRoomSelector,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


class VoiceRoomSelectorTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="selector-owner",
            email="selector-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="selector-member",
            email="selector-member@example.com",
            password=self.PASSWORD,
        )

        self.outsider = User.objects.create_user(
            username="selector-outsider",
            email="selector-outsider@example.com",
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

    def test_list_for_user_returns_member_rooms(self):
        rooms = list(
            VoiceRoomSelector.list_for_user(
                user=self.member,
            )
        )

        self.assertEqual(
            [room.id for room in rooms],
            [self.room.id],
        )

    def test_list_for_user_hides_non_member_rooms(self):
        rooms = list(
            VoiceRoomSelector.list_for_user(
                user=self.outsider,
            )
        )

        self.assertEqual(
            rooms,
            [],
        )

    def test_room_member_count_counts_all_members(self):
        room = (
            VoiceRoomSelector
            .get_for_member(
                user=self.member,
                room_id=self.room.id,
            )
        )

        self.assertIsNotNone(room)

        self.assertEqual(
            room.member_count,
            2,
        )

    def test_get_for_member_returns_none_for_outsider(self):
        room = (
            VoiceRoomSelector
            .get_for_member(
                user=self.outsider,
                room_id=self.room.id,
            )
        )

        self.assertIsNone(room)

    def test_list_members_returns_room_members(self):
        memberships = list(
            VoiceRoomSelector.list_members(
                room=self.room,
            )
        )

        self.assertEqual(
            {
                membership.user_id
                for membership
                in memberships
            },
            {
                self.owner.id,
                self.member.id,
            },
        )
