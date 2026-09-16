from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.api.v1.serializers import (
    VoiceRoomMembershipSerializer,
    VoiceRoomNameSerializer,
    VoiceRoomSerializer,
)
from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


class VoiceRoomSerializerTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="serializer-owner",
            email="serializer-owner@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def test_room_serializer_includes_uuid_and_owner(self):
        data = VoiceRoomSerializer(
            self.room
        ).data

        self.assertEqual(
            str(data["id"]),
            str(self.room.id),
        )

        self.assertEqual(
            data["name"],
            "Gaming",
        )

        self.assertEqual(
            data["owner"]["id"],
            self.owner.id,
        )

        self.assertEqual(
            data["member_count"],
            1,
        )

    def test_membership_serializer_includes_user(self):
        membership = (
            VoiceRoomMembership.objects.get(
                room=self.room,
                user=self.owner,
            )
        )

        data = (
            VoiceRoomMembershipSerializer(
                membership
            ).data
        )

        self.assertEqual(
            str(data["id"]),
            str(membership.id),
        )

        self.assertEqual(
            data["user"]["id"],
            self.owner.id,
        )

    def test_name_serializer_trims_whitespace(self):
        serializer = VoiceRoomNameSerializer(
            data={
                "name": "  Gaming  ",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        self.assertEqual(
            serializer.validated_data["name"],
            "Gaming",
        )

    def test_name_serializer_rejects_blank_name(self):
        serializer = VoiceRoomNameSerializer(
            data={
                "name": "   ",
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )
