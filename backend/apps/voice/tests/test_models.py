import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import GroupConversation
from apps.voice.models import VoiceParticipation, VoiceSession


User = get_user_model()


class VoiceSessionModelConstraintTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )
        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password=self.PASSWORD,
        )
        self.group = GroupConversation.objects.create(
            name="Voice Group",
        )

    def test_direct_session_rejects_same_caller_and_recipient(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.DIRECT,
                    status=VoiceSession.Status.RINGING,
                    caller=self.alice,
                    recipient=self.alice,
                    ring_expires_at=(
                        timezone.now() + timedelta(seconds=45)
                    ),
                )


    def test_direct_session_requires_ring_expiry(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.DIRECT,
                    status=VoiceSession.Status.RINGING,
                    caller=self.alice,
                    recipient=self.bob,
                )

    def test_group_session_cannot_be_ringing(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.GROUP,
                    status=VoiceSession.Status.RINGING,
                    group=self.group,
                )

    def test_active_session_requires_activated_timestamp(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.GROUP,
                    status=VoiceSession.Status.ACTIVE,
                    group=self.group,
                )

    def test_group_has_at_most_one_active_voice_session(self):
        VoiceSession.objects.create(
            kind=VoiceSession.Kind.GROUP,
            status=VoiceSession.Status.ACTIVE,
            group=self.group,
            activated_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceSession.objects.create(
                    kind=VoiceSession.Kind.GROUP,
                    status=VoiceSession.Status.ACTIVE,
                    group=self.group,
                    activated_at=timezone.now(),
                )


class VoiceParticipationModelConstraintTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )
        self.group_1 = GroupConversation.objects.create(
            name="Group One",
        )
        self.group_2 = GroupConversation.objects.create(
            name="Group Two",
        )
        self.session_1 = VoiceSession.objects.create(
            kind=VoiceSession.Kind.GROUP,
            status=VoiceSession.Status.ACTIVE,
            group=self.group_1,
            activated_at=timezone.now(),
        )
        self.session_2 = VoiceSession.objects.create(
            kind=VoiceSession.Kind.GROUP,
            status=VoiceSession.Status.ACTIVE,
            group=self.group_2,
            activated_at=timezone.now(),
        )

    def test_user_cannot_have_two_open_voice_participations(self):
        now = timezone.now()
        VoiceParticipation.objects.create(
            session=self.session_1,
            user=self.alice,
            role=VoiceParticipation.Role.MEMBER,
            client_instance_id=uuid.uuid4(),
            claimed_at=now,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceParticipation.objects.create(
                    session=self.session_2,
                    user=self.alice,
                    role=VoiceParticipation.Role.MEMBER,
                    client_instance_id=uuid.uuid4(),
                    claimed_at=timezone.now(),
                )

    def test_user_can_join_another_session_after_leaving(self):
        participation = VoiceParticipation.objects.create(
            session=self.session_1,
            user=self.alice,
            role=VoiceParticipation.Role.MEMBER,
            client_instance_id=uuid.uuid4(),
            claimed_at=timezone.now(),
        )
        participation.left_at = timezone.now()
        participation.save(update_fields=["left_at"])

        second = VoiceParticipation.objects.create(
            session=self.session_2,
            user=self.alice,
            role=VoiceParticipation.Role.MEMBER,
            client_instance_id=uuid.uuid4(),
            claimed_at=timezone.now(),
        )

        self.assertIsNone(second.left_at)

    def test_claim_id_and_timestamp_must_be_set_together(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VoiceParticipation.objects.create(
                    session=self.session_1,
                    user=self.alice,
                    role=VoiceParticipation.Role.MEMBER,
                    client_instance_id=uuid.uuid4(),
                    claimed_at=None,
                )
