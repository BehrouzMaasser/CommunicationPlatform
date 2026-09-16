from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.voice.models import (
    VoiceRoom,
    VoiceRoomInvitation,
    VoiceRoomInvitationLink,
    VoiceRoomMembership,
)


User = get_user_model()


class VoiceRoomModelTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="voice-room-owner",
            email="voice-room-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="voice-room-member",
            email="voice-room-member@example.com",
            password=self.PASSWORD,
        )

        self.other_user = User.objects.create_user(
            username="voice-room-other",
            email="voice-room-other@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoom.objects.create(
            name="Gaming",
            owner=self.owner,
        )

    def test_new_voice_room_domain_uses_uuid7_ids(self):
        membership = VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.owner,
        )

        invitation = VoiceRoomInvitation.objects.create(
            room=self.room,
            invited_by=self.owner,
            recipient=self.member,
        )

        link = VoiceRoomInvitationLink.objects.create(
            room=self.room,
            created_by=self.owner,
            token_hash="a" * 64,
            expires_at=(
                timezone.now()
                + timedelta(days=1)
            ),
        )

        self.assertEqual(self.room.id.version, 7)
        self.assertEqual(membership.id.version, 7)
        self.assertEqual(invitation.id.version, 7)
        self.assertEqual(link.id.version, 7)

    def test_room_has_exact_owner_field(self):
        self.assertEqual(
            self.room.owner,
            self.owner,
        )

    def test_membership_is_unique_per_room_and_user(self):
        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceRoomMembership.objects.create(
                    room=self.room,
                    user=self.member,
                )

    def test_room_members_relation_uses_memberships(self):
        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.owner,
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

        self.assertEqual(
            set(self.room.members.all()),
            {
                self.owner,
                self.member,
            },
        )

    def test_user_cannot_invite_themselves(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceRoomInvitation.objects.create(
                    room=self.room,
                    invited_by=self.owner,
                    recipient=self.owner,
                )

    def test_only_one_pending_invitation_per_room_recipient(self):
        VoiceRoomInvitation.objects.create(
            room=self.room,
            invited_by=self.owner,
            recipient=self.member,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceRoomInvitation.objects.create(
                    room=self.room,
                    invited_by=self.other_user,
                    recipient=self.member,
                )

    def test_invitation_link_hash_is_unique(self):
        VoiceRoomInvitationLink.objects.create(
            room=self.room,
            created_by=self.owner,
            token_hash="b" * 64,
            expires_at=(
                timezone.now()
                + timedelta(days=1)
            ),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceRoomInvitationLink.objects.create(
                    room=self.room,
                    created_by=self.owner,
                    token_hash="b" * 64,
                    expires_at=(
                        timezone.now()
                        + timedelta(days=1)
                    ),
                )
