from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.friendships.models import Friendship
from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation import (
    VoiceRoomInvitationService,
)


User = get_user_model()


class VoiceRoomInvitationRealtimeTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="invite-rt-owner",
            email="invite-rt-owner@example.com",
            password=self.PASSWORD,
        )

        self.recipient = User.objects.create_user(
            username="invite-rt-recipient",
            email="invite-rt-recipient@example.com",
            password=self.PASSWORD,
        )

        user_1_id, user_2_id = sorted(
            [
                self.owner.pk,
                self.recipient.pk,
            ]
        )

        Friendship.objects.create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "VoiceRoomRealtimePublisher."
        "invitation_created_after_commit"
    )
    def test_create_invitation_publishes_event(
        self,
        publish,
    ):
        invitation = (
            VoiceRoomInvitationService
            .create_invitation(
                current_user=self.owner,
                room_id=self.room.pk,
                target_user_id=self.recipient.pk,
            )
        )

        publish.assert_called_once_with(
            invitation_id=invitation.pk,
            room_id=self.room.pk,
            room_name="Gaming",
            invited_by_id=self.owner.pk,
            recipient_id=self.recipient.pk,
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "VoiceRoomRealtimePublisher."
        "member_added_after_commit"
    )
    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "VoiceRoomRealtimePublisher."
        "invitation_accepted_after_commit"
    )
    def test_accept_publishes_accept_and_member_added(
        self,
        accepted,
        member_added,
    ):
        invitation = (
            VoiceRoomInvitationService
            .create_invitation(
                current_user=self.owner,
                room_id=self.room.pk,
                target_user_id=self.recipient.pk,
            )
        )

        VoiceRoomInvitationService.accept_invitation(
            current_user=self.recipient,
            invitation_id=invitation.pk,
        )

        accepted.assert_called_once_with(
            invitation_id=invitation.pk,
            room_id=self.room.pk,
            room_name="Gaming",
            invited_by_id=self.owner.pk,
            recipient_id=self.recipient.pk,
        )

        member_added.assert_called_once_with(
            room_id=self.room.pk,
            member_user_id=self.recipient.pk,
            audience_user_ids=sorted(
                [
                    self.owner.pk,
                    self.recipient.pk,
                ]
            ),
        )

        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.recipient,
            ).exists()
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "VoiceRoomRealtimePublisher."
        "invitation_cancelled_after_commit"
    )
    def test_cancel_invitation_publishes_event(
        self,
        publish,
    ):
        invitation = (
            VoiceRoomInvitationService
            .create_invitation(
                current_user=self.owner,
                room_id=self.room.pk,
                target_user_id=self.recipient.pk,
            )
        )

        VoiceRoomInvitationService.cancel_invitation(
            current_user=self.owner,
            room_id=self.room.pk,
            invitation_id=invitation.pk,
        )

        publish.assert_called_once_with(
            invitation_id=invitation.pk,
            room_id=self.room.pk,
            invited_by_id=self.owner.pk,
            recipient_id=self.recipient.pk,
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation."
        "VoiceRoomRealtimePublisher."
        "invitation_rejected_after_commit"
    )
    def test_reject_invitation_publishes_event(
        self,
        publish,
    ):
        invitation = (
            VoiceRoomInvitationService
            .create_invitation(
                current_user=self.owner,
                room_id=self.room.pk,
                target_user_id=self.recipient.pk,
            )
        )

        VoiceRoomInvitationService.reject_invitation(
            current_user=self.recipient,
            invitation_id=invitation.pk,
        )

        publish.assert_called_once_with(
            invitation_id=invitation.pk,
            room_id=self.room.pk,
            invited_by_id=self.owner.pk,
            recipient_id=self.recipient.pk,
        )
