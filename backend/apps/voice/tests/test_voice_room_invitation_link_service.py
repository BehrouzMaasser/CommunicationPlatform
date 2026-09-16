from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from uuid6 import uuid7

from apps.voice.exceptions import (
    InvalidVoiceRoomInvitationLink,
    VoiceRoomInvitationLinkNotFound,
    VoiceRoomOwnerRequired,
)
from apps.voice.models import (
    VoiceRoomInvitation,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation_link import (
    VoiceRoomInvitationLinkService,
)


User = get_user_model()


class VoiceRoomInvitationLinkServiceTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="link-owner",
            email="link-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="link-member",
            email="link-member@example.com",
            password=self.PASSWORD,
        )

        self.other_user = User.objects.create_user(
            username="link-other",
            email="link-other@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def create_link(self):
        return (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.id,
            )
        )

    def test_owner_can_create_link_and_recover_token(self):
        link, token = self.create_link()

        self.assertNotEqual(
            link.token_hash,
            token,
        )

        self.assertEqual(
            (
                VoiceRoomInvitationLinkService
                .recover_token(
                    link=link,
                )
            ),
            token,
        )

    def test_non_owner_cannot_create_link(self):
        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            (
                VoiceRoomInvitationLinkService
                .create_link(
                    current_user=self.member,
                    room_id=self.room.id,
                )
            )

    def test_user_can_join_room_with_valid_link(self):
        _, token = self.create_link()

        membership, created = (
            VoiceRoomInvitationLinkService
            .join_with_token(
                current_user=self.member,
                token=token,
            )
        )

        self.assertTrue(created)
        self.assertEqual(
            membership.room,
            self.room,
        )
        self.assertEqual(
            membership.user,
            self.member,
        )

    def test_existing_member_join_is_idempotent(self):
        existing = (
            VoiceRoomMembership.objects.create(
                room=self.room,
                user=self.member,
            )
        )

        _, token = self.create_link()

        membership, created = (
            VoiceRoomInvitationLinkService
            .join_with_token(
                current_user=self.member,
                token=token,
            )
        )

        self.assertFalse(created)
        self.assertEqual(
            membership.id,
            existing.id,
        )

    def test_link_join_removes_pending_direct_invitation(self):
        invitation = (
            VoiceRoomInvitation.objects.create(
                room=self.room,
                invited_by=self.owner,
                recipient=self.member,
            )
        )

        _, token = self.create_link()

        (
            VoiceRoomInvitationLinkService
            .join_with_token(
                current_user=self.member,
                token=token,
            )
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_expired_link_cannot_be_used(self):
        link, token = self.create_link()

        link.expires_at = (
            timezone.now()
            - timedelta(seconds=1)
        )
        link.save(
            update_fields=[
                "expires_at",
            ],
        )

        with self.assertRaises(
            InvalidVoiceRoomInvitationLink
        ):
            (
                VoiceRoomInvitationLinkService
                .join_with_token(
                    current_user=self.member,
                    token=token,
                )
            )

    def test_revoked_link_cannot_be_used(self):
        link, token = self.create_link()

        (
            VoiceRoomInvitationLinkService
            .revoke_link(
                current_user=self.owner,
                room_id=self.room.id,
                link_id=link.id,
            )
        )

        with self.assertRaises(
            InvalidVoiceRoomInvitationLink
        ):
            (
                VoiceRoomInvitationLinkService
                .join_with_token(
                    current_user=self.member,
                    token=token,
                )
            )

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(
            InvalidVoiceRoomInvitationLink
        ):
            (
                VoiceRoomInvitationLinkService
                .join_with_token(
                    current_user=self.member,
                    token="not-a-real-token",
                )
            )

    def test_non_owner_cannot_revoke_link(self):
        link, _ = self.create_link()

        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            (
                VoiceRoomInvitationLinkService
                .revoke_link(
                    current_user=self.member,
                    room_id=self.room.id,
                    link_id=link.id,
                )
            )

    def test_missing_link_cannot_be_revoked(self):
        with self.assertRaises(
            VoiceRoomInvitationLinkNotFound
        ):
            (
                VoiceRoomInvitationLinkService
                .revoke_link(
                    current_user=self.owner,
                    room_id=self.room.id,
                    link_id=uuid7(),
                )
            )
