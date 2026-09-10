from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import (
    GroupConversation,
    GroupInvitation,
    GroupInvitationLink,
)


User = get_user_model()


class GroupInvitationModelConstraintTests(TestCase):
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
            name="Study Group",
        )

    def test_inviter_cannot_invite_themselves(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupInvitation.objects.create(
                    group=self.group,
                    invited_by=self.alice,
                    recipient=self.alice,
                )

        self.assertFalse(
            GroupInvitation.objects.exists()
        )

    def test_only_one_pending_invitation_per_group_and_recipient(self):
        GroupInvitation.objects.create(
            group=self.group,
            invited_by=self.alice,
            recipient=self.bob,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupInvitation.objects.create(
                    group=self.group,
                    invited_by=self.alice,
                    recipient=self.bob,
                )

        self.assertEqual(
            GroupInvitation.objects.count(),
            1,
        )

    def test_same_recipient_can_have_invitations_to_different_groups(self):
        second_group = GroupConversation.objects.create(
            name="Second Group",
        )

        GroupInvitation.objects.create(
            group=self.group,
            invited_by=self.alice,
            recipient=self.bob,
        )

        GroupInvitation.objects.create(
            group=second_group,
            invited_by=self.alice,
            recipient=self.bob,
        )

        self.assertEqual(
            GroupInvitation.objects.count(),
            2,
        )


class GroupInvitationLinkModelConstraintTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )

        self.group = GroupConversation.objects.create(
            name="Study Group",
        )

    def test_token_hash_must_be_unique(self):
        GroupInvitationLink.objects.create(
            group=self.group,
            created_by=self.alice,
            token_hash="a" * 64,
            expires_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupInvitationLink.objects.create(
                    group=self.group,
                    created_by=self.alice,
                    token_hash="a" * 64,
                    expires_at=timezone.now(),
                )

        self.assertEqual(
            GroupInvitationLink.objects.count(),
            1,
        )
