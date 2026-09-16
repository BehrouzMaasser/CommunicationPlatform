from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.voice.models import (
    VoiceRoomInvitation,
)
from apps.voice.selectors.voice_room_invitation import (
    VoiceRoomInvitationSelector,
)
from apps.voice.selectors.voice_room_invitation_link import (
    VoiceRoomInvitationLinkSelector,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation_link import (
    VoiceRoomInvitationLinkService,
)


User = get_user_model()


class VoiceRoomInvitationSelectorTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="selector-invite-owner",
            email="selector-invite-owner@example.com",
            password=self.PASSWORD,
        )

        self.recipient = User.objects.create_user(
            username="selector-invite-recipient",
            email="selector-invite-recipient@example.com",
            password=self.PASSWORD,
        )

        self.other = User.objects.create_user(
            username="selector-invite-other",
            email="selector-invite-other@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        self.invitation = (
            VoiceRoomInvitation.objects.create(
                room=self.room,
                invited_by=self.owner,
                recipient=self.recipient,
            )
        )

    def test_recipient_list_returns_only_their_invitations(self):
        VoiceRoomInvitation.objects.create(
            room=self.room,
            invited_by=self.owner,
            recipient=self.other,
        )

        invitations = list(
            VoiceRoomInvitationSelector
            .list_for_recipient(
                user=self.recipient,
            )
        )

        self.assertEqual(
            [
                invitation.id
                for invitation
                in invitations
            ],
            [
                self.invitation.id,
            ],
        )

    def test_room_list_returns_room_invitations(self):
        other_room = (
            VoiceRoomService.create_room(
                current_user=self.owner,
                name="Study",
            )
        )

        VoiceRoomInvitation.objects.create(
            room=other_room,
            invited_by=self.owner,
            recipient=self.other,
        )

        invitations = list(
            VoiceRoomInvitationSelector
            .list_for_room(
                room=self.room,
            )
        )

        self.assertEqual(
            [
                invitation.id
                for invitation
                in invitations
            ],
            [
                self.invitation.id,
            ],
        )


class VoiceRoomInvitationLinkSelectorTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="selector-link-owner",
            email="selector-link-owner@example.com",
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

    def test_active_link_is_listed(self):
        link, _ = self.create_link()

        links = list(
            VoiceRoomInvitationLinkSelector
            .list_active_for_room(
                room=self.room,
            )
        )

        self.assertEqual(
            [
                item.id
                for item
                in links
            ],
            [
                link.id,
            ],
        )

    def test_revoked_link_is_not_listed(self):
        link, _ = self.create_link()

        (
            VoiceRoomInvitationLinkService
            .revoke_link(
                current_user=self.owner,
                room_id=self.room.id,
                link_id=link.id,
            )
        )

        self.assertFalse(
            VoiceRoomInvitationLinkSelector
            .list_active_for_room(
                room=self.room,
            )
            .exists()
        )

    def test_expired_link_is_not_listed(self):
        link, _ = self.create_link()

        link.expires_at = (
            timezone.now()
            - timedelta(seconds=1)
        )
        link.save(
            update_fields=[
                "expires_at",
            ],
        )

        self.assertFalse(
            VoiceRoomInvitationLinkSelector
            .list_active_for_room(
                room=self.room,
            )
            .exists()
        )
