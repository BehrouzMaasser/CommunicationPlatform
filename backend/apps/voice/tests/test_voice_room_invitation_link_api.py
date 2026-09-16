from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.voice.models import (
    VoiceRoomInvitationLink,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation_link import (
    VoiceRoomInvitationLinkService,
)


User = get_user_model()


@override_settings(
    VOICE_ENABLED=True
)
class VoiceRoomInvitationLinkApiTests(
    APITestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="link-api-owner",
            email="link-api-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="link-api-member",
            email="link-api-member@example.com",
            password=self.PASSWORD,
        )

        self.outsider = User.objects.create_user(
            username="link-api-outsider",
            email="link-api-outsider@example.com",
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

    def authenticate(self, user):
        self.client.force_authenticate(
            user=user,
        )

    def create_link(self):
        return (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.id,
            )
        )

    def test_owner_can_create_invite_link(self):
        self.authenticate(
            self.owner
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            response.data["token"]
        )

        self.assertTrue(
            VoiceRoomInvitationLink.objects.filter(
                pk=response.data["id"],
            ).exists()
        )

    def test_non_owner_cannot_create_invite_link(self):
        self.authenticate(
            self.member
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_create_returns_404(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_owner_can_list_active_links_and_recover_token(
        self,
    ):
        link, token = self.create_link()

        self.authenticate(
            self.owner
        )

        response = self.client.get(
            reverse(
                "voice-room-invite-link-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        item = response.data["results"][0]

        self.assertEqual(
            item["id"],
            str(link.id),
        )

        self.assertEqual(
            item["token"],
            token,
        )

    def test_non_owner_cannot_list_links(self):
        self.authenticate(
            self.member
        )

        response = self.client.get(
            reverse(
                "voice-room-invite-link-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_revoke_link(self):
        link, _ = self.create_link()

        self.authenticate(
            self.owner
        )

        response = self.client.delete(
            reverse(
                "voice-room-invite-link-revoke",
                kwargs={
                    "room_id": self.room.id,
                    "link_id": link.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        link.refresh_from_db()

        self.assertIsNotNone(
            link.revoked_at
        )

    def test_non_owner_cannot_revoke_link(self):
        link, _ = self.create_link()

        self.authenticate(
            self.member
        )

        response = self.client.delete(
            reverse(
                "voice-room-invite-link-revoke",
                kwargs={
                    "room_id": self.room.id,
                    "link_id": link.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_valid_link_adds_user_to_room(self):
        _, token = self.create_link()

        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-join"
            ),
            {
                "token": token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            response.data["created"]
        )

        self.assertEqual(
            response.data["room"]["id"],
            str(self.room.id),
        )

        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.outsider,
            ).exists()
        )

    def test_existing_member_join_is_idempotent(self):
        _, token = self.create_link()

        self.authenticate(
            self.member
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-join"
            ),
            {
                "token": token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.data["created"]
        )

    def test_invalid_token_returns_400(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-join"
            ),
            {
                "token": "definitely-not-valid",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["code"],
            "INVALID_VOICE_ROOM_INVITATION_LINK",
        )

    def test_revoked_token_returns_400(self):
        link, token = self.create_link()

        (
            VoiceRoomInvitationLinkService
            .revoke_link(
                current_user=self.owner,
                room_id=self.room.id,
                link_id=link.id,
            )
        )

        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-join"
            ),
            {
                "token": token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["code"],
            "INVALID_VOICE_ROOM_INVITATION_LINK",
        )

    def test_blank_token_returns_400(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invite-link-join"
            ),
            {
                "token": "   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )
