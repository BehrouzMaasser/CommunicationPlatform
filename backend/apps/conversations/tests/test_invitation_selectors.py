from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import (
    GroupInvitation,
    GroupInvitationLink,
)
from apps.conversations.selectors import (
    GroupInvitationLinkSelector,
    GroupInvitationSelector,
)
from apps.conversations.services import (
    GroupConversationService,
)


User = get_user_model()


class GroupInvitationSelectorTests(TestCase):
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
        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password=self.PASSWORD,
        )

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

    def test_list_incoming_returns_only_recipient_invitations(self):
        bob_invitation = GroupInvitation.objects.create(
            group=self.group,
            invited_by=self.alice,
            recipient=self.bob,
        )

        GroupInvitation.objects.create(
            group=self.group,
            invited_by=self.alice,
            recipient=self.charlie,
        )

        incoming = list(
            GroupInvitationSelector.list_incoming(
                user=self.bob,
            )
        )

        self.assertEqual(
            incoming,
            [bob_invitation],
        )

    def test_pending_exists(self):
        GroupInvitation.objects.create(
            group=self.group,
            invited_by=self.alice,
            recipient=self.bob,
        )

        self.assertTrue(
            GroupInvitationSelector.pending_exists(
                group_id=self.group.pk,
                user=self.bob,
            )
        )

        self.assertFalse(
            GroupInvitationSelector.pending_exists(
                group_id=self.group.pk,
                user=self.charlie,
            )
        )


class GroupInvitationLinkSelectorTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.other_group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Other Group",
        )

    def test_list_for_group_returns_only_that_groups_links(self):
        older = GroupInvitationLink.objects.create(
            group=self.group,
            created_by=self.alice,
            token_hash="a" * 64,
            expires_at=timezone.now() + timedelta(days=1),
        )

        newer = GroupInvitationLink.objects.create(
            group=self.group,
            created_by=self.alice,
            token_hash="b" * 64,
            expires_at=timezone.now() + timedelta(days=1),
        )

        GroupInvitationLink.objects.create(
            group=self.other_group,
            created_by=self.alice,
            token_hash="c" * 64,
            expires_at=timezone.now() + timedelta(days=1),
        )

        links = list(
            GroupInvitationLinkSelector.list_for_group(
                group=self.group,
            )
        )

        self.assertEqual(
            links,
            [
                newer,
                older,
            ],
        )
