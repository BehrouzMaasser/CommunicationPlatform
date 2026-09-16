from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.exceptions import (
    UserAlreadyVoiceRoomMember,
    VoiceRoomFriendshipRequired,
    VoiceRoomInvitationAlreadyPending,
    VoiceRoomInvitationNotFound,
    VoiceRoomInvitationRecipientRequired,
    VoiceRoomInvitationTargetNotFound,
    VoiceRoomOwnerRequired,
)
from apps.voice.models import (
    VoiceRoomInvitation,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation import (
    VoiceRoomInvitationService,
)


User = get_user_model()


class VoiceRoomInvitationServiceTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="invite-owner",
            email="invite-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="invite-member",
            email="invite-member@example.com",
            password=self.PASSWORD,
        )

        self.other_user = User.objects.create_user(
            username="invite-other",
            email="invite-other@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def create_invitation(
        self,
        *,
        target=None,
    ):
        target = target or self.member

        with patch(
            "apps.voice.services."
            "voice_room_invitation."
            "FriendshipSelector."
            "exists_between_users",
            return_value=True,
        ):
            return (
                VoiceRoomInvitationService
                .create_invitation(
                    current_user=self.owner,
                    room_id=self.room.id,
                    target_user_id=target.id,
                )
            )

    def test_owner_can_invite_friend(self):
        invitation = self.create_invitation()

        self.assertEqual(
            invitation.room,
            self.room,
        )
        self.assertEqual(
            invitation.invited_by,
            self.owner,
        )
        self.assertEqual(
            invitation.recipient,
            self.member,
        )

    def test_non_friend_cannot_be_invited(self):
        with patch(
            "apps.voice.services."
            "voice_room_invitation."
            "FriendshipSelector."
            "exists_between_users",
            return_value=False,
        ):
            with self.assertRaises(
                VoiceRoomFriendshipRequired
            ):
                (
                    VoiceRoomInvitationService
                    .create_invitation(
                        current_user=self.owner,
                        room_id=self.room.id,
                        target_user_id=self.member.id,
                    )
                )

    def test_non_owner_cannot_invite(self):
        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            (
                VoiceRoomInvitationService
                .create_invitation(
                    current_user=self.member,
                    room_id=self.room.id,
                    target_user_id=self.other_user.id,
                )
            )

    def test_existing_member_cannot_be_invited(self):
        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

        with self.assertRaises(
            UserAlreadyVoiceRoomMember
        ):
            (
                VoiceRoomInvitationService
                .create_invitation(
                    current_user=self.owner,
                    room_id=self.room.id,
                    target_user_id=self.member.id,
                )
            )

    def test_duplicate_invitation_is_rejected(self):
        self.create_invitation()

        with self.assertRaises(
            VoiceRoomInvitationAlreadyPending
        ):
            self.create_invitation()

    def test_missing_target_is_rejected(self):
        with self.assertRaises(
            VoiceRoomInvitationTargetNotFound
        ):
            (
                VoiceRoomInvitationService
                .create_invitation(
                    current_user=self.owner,
                    room_id=self.room.id,
                    target_user_id=999999999,
                )
            )

    def test_recipient_can_accept_invitation(self):
        invitation = self.create_invitation()

        membership = (
            VoiceRoomInvitationService
            .accept_invitation(
                current_user=self.member,
                invitation_id=invitation.id,
            )
        )

        self.assertEqual(
            membership.room,
            self.room,
        )
        self.assertEqual(
            membership.user,
            self.member,
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_other_user_cannot_accept_invitation(self):
        invitation = self.create_invitation()

        with self.assertRaises(
            VoiceRoomInvitationRecipientRequired
        ):
            (
                VoiceRoomInvitationService
                .accept_invitation(
                    current_user=self.other_user,
                    invitation_id=invitation.id,
                )
            )

    def test_recipient_can_reject_invitation(self):
        invitation = self.create_invitation()

        (
            VoiceRoomInvitationService
            .reject_invitation(
                current_user=self.member,
                invitation_id=invitation.id,
            )
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_owner_can_cancel_invitation(self):
        invitation = self.create_invitation()

        (
            VoiceRoomInvitationService
            .cancel_invitation(
                current_user=self.owner,
                room_id=self.room.id,
                invitation_id=invitation.id,
            )
        )

        self.assertFalse(
            VoiceRoomInvitation.objects.filter(
                pk=invitation.id,
            ).exists()
        )

    def test_non_owner_cannot_cancel_invitation(self):
        invitation = self.create_invitation()

        with self.assertRaises(
            VoiceRoomOwnerRequired
        ):
            (
                VoiceRoomInvitationService
                .cancel_invitation(
                    current_user=self.member,
                    room_id=self.room.id,
                    invitation_id=invitation.id,
                )
            )

    def test_missing_invitation_raises_domain_error(self):
        invitation = self.create_invitation()
        invitation_id = invitation.id
        invitation.delete()

        with self.assertRaises(
            VoiceRoomInvitationNotFound
        ):
            (
                VoiceRoomInvitationService
                .accept_invitation(
                    current_user=self.member,
                    invitation_id=invitation_id,
                )
            )
