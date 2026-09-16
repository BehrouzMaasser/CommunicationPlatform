from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.api.v1.serializers import (
    VoiceRoomInvitationCreateSerializer,
    VoiceRoomInvitationLinkJoinSerializer,
    VoiceRoomInvitationLinkSerializer,
    VoiceRoomInvitationSerializer,
)
from apps.voice.models import (
    VoiceRoomInvitation,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation_link import (
    VoiceRoomInvitationLinkService,
)


User = get_user_model()


class VoiceRoomInvitationSerializerTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="serializer-invite-owner",
            email="serializer-invite-owner@example.com",
            password=self.PASSWORD,
        )

        self.recipient = User.objects.create_user(
            username="serializer-invite-recipient",
            email="serializer-invite-recipient@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def test_invitation_serializer_contains_room_and_users(self):
        invitation = (
            VoiceRoomInvitation.objects.create(
                room=self.room,
                invited_by=self.owner,
                recipient=self.recipient,
            )
        )

        data = VoiceRoomInvitationSerializer(
            invitation
        ).data

        self.assertEqual(
            str(data["id"]),
            str(invitation.id),
        )

        self.assertEqual(
            data["room_id"],
            str(self.room.id),
        )

        self.assertEqual(
            data["room_name"],
            "Gaming",
        )

        self.assertEqual(
            data["invited_by"]["id"],
            self.owner.id,
        )

        self.assertEqual(
            data["recipient"]["id"],
            self.recipient.id,
        )

    def test_create_serializer_accepts_user_id(self):
        serializer = (
            VoiceRoomInvitationCreateSerializer(
                data={
                    "user_id": self.recipient.id,
                }
            )
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_link_serializer_recovers_token(self):
        link, token = (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.id,
            )
        )

        data = VoiceRoomInvitationLinkSerializer(
            link
        ).data

        self.assertEqual(
            data["token"],
            token,
        )

    def test_link_join_serializer_rejects_blank_token(self):
        serializer = (
            VoiceRoomInvitationLinkJoinSerializer(
                data={
                    "token": "   ",
                }
            )
        )

        self.assertFalse(
            serializer.is_valid()
        )
