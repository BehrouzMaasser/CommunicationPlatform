from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.voice.models import (
    VoiceRoomInvitation,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


@override_settings(
    VOICE_ENABLED=True
)
class VoiceRoomInvitationApiTests(
    APITestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="invite-api-owner",
            email="invite-api-owner@example.com",
            password=self.PASSWORD,
        )

        self.recipient = User.objects.create_user(
            username="invite-api-recipient",
            email="invite-api-recipient@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="invite-api-member",
            email="invite-api-member@example.com",
            password=self.PASSWORD,
        )

        self.outsider = User.objects.create_user(
            username="invite-api-outsider",
            email="invite-api-outsider@example.com",
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

    def create_invitation(
        self,
        *,
        recipient=None,
    ):
        recipient = (
            recipient
            or self.recipient
        )

        return (
            VoiceRoomInvitation.objects.create(
                room=self.room,
                invited_by=self.owner,
                recipient=recipient,
            )
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "FriendshipSelector."
        "exists_between_users",
        return_value=True,
    )
    def test_owner_can_create_invitation(
        self,
        friendship_exists,
    ):
        self.authenticate(
            self.owner
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "user_id": self.recipient.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            VoiceRoomInvitation.objects.filter(
                room=self.room,
                recipient=self.recipient,
            ).exists()
        )

        friendship_exists.assert_called_once()

    def test_non_owner_member_cannot_create_invitation(
        self,
    ):
        self.authenticate(
            self.member
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "user_id": self.recipient.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_create_invitation_returns_404(
        self,
    ):
        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "user_id": self.recipient.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_owner_can_list_pending_room_invitations(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.owner
        )

        response = self.client.get(
            reverse(
                "voice-room-invitation-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = {
            item["id"]
            for item
            in response.data["results"]
        }

        self.assertEqual(
            returned_ids,
            {
                str(invitation.id),
            },
        )

    def test_non_owner_member_cannot_list_room_invitations(
        self,
    ):
        self.authenticate(
            self.member
        )

        response = self.client.get(
            reverse(
                "voice-room-invitation-collection",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_recipient_lists_only_their_invitations(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.create_invitation(
            recipient=self.outsider,
        )

        self.authenticate(
            self.recipient
        )

        response = self.client.get(
            reverse(
                "voice-room-incoming-invitation-list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = {
            item["id"]
            for item
            in response.data["results"]
        }

        self.assertEqual(
            returned_ids,
            {
                str(invitation.id),
            },
        )

    def test_recipient_can_accept_invitation(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.recipient
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-accept",
                kwargs={
                    "invitation_id": (
                        invitation.id
                    ),
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
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.recipient,
            ).exists()
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_other_user_cannot_accept_invitation(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-accept",
                kwargs={
                    "invitation_id": (
                        invitation.id
                    ),
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_recipient_can_reject_invitation(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.recipient
        )

        response = self.client.post(
            reverse(
                "voice-room-invitation-reject",
                kwargs={
                    "invitation_id": (
                        invitation.id
                    ),
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_owner_can_cancel_invitation(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.owner
        )

        response = self.client.delete(
            reverse(
                "voice-room-invitation-cancel",
                kwargs={
                    "room_id": self.room.id,
                    "invitation_id": (
                        invitation.id
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_non_owner_cannot_cancel_invitation(
        self,
    ):
        invitation = (
            self.create_invitation()
        )

        self.authenticate(
            self.member
        )

        response = self.client.delete(
            reverse(
                "voice-room-invitation-cancel",
                kwargs={
                    "room_id": self.room.id,
                    "invitation_id": (
                        invitation.id
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )
