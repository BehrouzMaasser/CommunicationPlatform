from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_room_invitation_link import (
    VoiceRoomInvitationLinkService,
)


User = get_user_model()


class VoiceRoomInviteLinkRealtimeTests(
    TestCase
):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="link-rt-owner",
            email="link-rt-owner@example.com",
            password=self.PASSWORD,
        )

        self.joiner = User.objects.create_user(
            username="link-rt-joiner",
            email="link-rt-joiner@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation_link."
        "VoiceRoomRealtimePublisher."
        "invite_link_created_after_commit"
    )
    def test_create_link_publishes_event(
        self,
        publish,
    ):
        link, _token = (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.pk,
            )
        )

        publish.assert_called_once_with(
            link_id=link.pk,
            room_id=self.room.pk,
            owner_id=self.owner.pk,
            expires_at=link.expires_at,
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation_link."
        "VoiceRoomRealtimePublisher."
        "member_added_after_commit"
    )
    def test_new_link_join_publishes_member_added(
        self,
        publish,
    ):
        _link, token = (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.pk,
            )
        )

        membership, created = (
            VoiceRoomInvitationLinkService
            .join_with_token(
                current_user=self.joiner,
                token=token,
            )
        )

        self.assertTrue(created)

        self.assertEqual(
            membership.user_id,
            self.joiner.pk,
        )

        publish.assert_called_once_with(
            room_id=self.room.pk,
            member_user_id=self.joiner.pk,
            audience_user_ids=sorted(
                [
                    self.owner.pk,
                    self.joiner.pk,
                ]
            ),
        )

    @patch(
        "apps.voice.services."
        "voice_room_invitation_link."
        "VoiceRoomRealtimePublisher."
        "member_added_after_commit"
    )
    def test_existing_member_link_join_does_not_publish(
        self,
        publish,
    ):
        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.joiner,
        )

        _link, token = (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.pk,
            )
        )

        _membership, created = (
            VoiceRoomInvitationLinkService
            .join_with_token(
                current_user=self.joiner,
                token=token,
            )
        )

        self.assertFalse(created)
        publish.assert_not_called()

    @patch(
        "apps.voice.services."
        "voice_room_invitation_link."
        "VoiceRoomRealtimePublisher."
        "invite_link_revoked_after_commit"
    )
    def test_revoke_publishes_only_on_state_change(
        self,
        publish,
    ):
        link, _token = (
            VoiceRoomInvitationLinkService
            .create_link(
                current_user=self.owner,
                room_id=self.room.pk,
            )
        )

        VoiceRoomInvitationLinkService.revoke_link(
            current_user=self.owner,
            room_id=self.room.pk,
            link_id=link.pk,
        )

        publish.assert_called_once_with(
            link_id=link.pk,
            room_id=self.room.pk,
            owner_id=self.owner.pk,
        )

        VoiceRoomInvitationLinkService.revoke_link(
            current_user=self.owner,
            room_id=self.room.pk,
            link_id=link.pk,
        )

        self.assertEqual(
            publish.call_count,
            1,
        )
