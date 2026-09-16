from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import (
    GroupConversation,
)
from apps.voice.models import (
    VoiceRoom,
    VoiceSession,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


class VoiceRoomSessionModelTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="room-session-owner",
            email="room-session-owner@example.com",
            password=self.PASSWORD,
        )

        self.other = User.objects.create_user(
            username="room-session-other",
            email="room-session-other@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

    def test_room_session_can_reference_voice_room(self):
        session = VoiceSession.objects.create(
            kind=VoiceSession.Kind.ROOM,
            status=VoiceSession.Status.ACTIVE,
            voice_room=self.room,
            activated_at=timezone.now(),
        )

        self.assertEqual(
            session.voice_room,
            self.room,
        )

        self.assertIsNone(
            session.group_id
        )

    def test_only_one_active_session_per_voice_room(self):
        VoiceSession.objects.create(
            kind=VoiceSession.Kind.ROOM,
            status=VoiceSession.Status.ACTIVE,
            voice_room=self.room,
            activated_at=timezone.now(),
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.ROOM,
                    status=VoiceSession.Status.ACTIVE,
                    voice_room=self.room,
                    activated_at=timezone.now(),
                )

    def test_room_session_requires_voice_room(self):
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.ROOM,
                    status=VoiceSession.Status.ACTIVE,
                    activated_at=timezone.now(),
                )

    def test_room_session_cannot_reference_legacy_group(self):
        legacy_group = (
            GroupConversation.objects.create(
                name="Legacy",
            )
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.ROOM,
                    status=VoiceSession.Status.ACTIVE,
                    group=legacy_group,
                    voice_room=self.room,
                    activated_at=timezone.now(),
                )

    def test_direct_session_cannot_reference_voice_room(self):
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.DIRECT,
                    status=VoiceSession.Status.RINGING,
                    caller=self.owner,
                    recipient=self.other,
                    voice_room=self.room,
                    ring_expires_at=(
                        timezone.now()
                    ),
                )

    def test_room_session_cannot_be_ringing(self):
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.ROOM,
                    status=VoiceSession.Status.RINGING,
                    voice_room=self.room,
                )
