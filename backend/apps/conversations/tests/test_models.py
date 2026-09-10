from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)


User = get_user_model()


class DirectConversationModelConstraintTests(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )

        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password="Strong-Test-Password!123",
        )

    def test_self_direct_conversation_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DirectConversation.objects.create(
                    user_1=self.alice,
                    user_2=self.alice,
                )

        self.assertEqual(
            DirectConversation.objects.count(),
            0,
        )

    def test_non_canonical_direct_conversation_is_rejected(self):
        lower_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DirectConversation.objects.create(
                    user_1=higher_user,
                    user_2=lower_user,
                )

        self.assertEqual(
            DirectConversation.objects.count(),
            0,
        )

    def test_canonical_direct_conversation_is_allowed(self):
        lower_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        conversation = DirectConversation.objects.create(
            user_1=lower_user,
            user_2=higher_user,
        )

        self.assertEqual(
            conversation.user_1,
            lower_user,
        )

        self.assertEqual(
            conversation.user_2,
            higher_user,
        )

    def test_duplicate_direct_conversation_is_rejected(self):
        lower_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        DirectConversation.objects.create(
            user_1=lower_user,
            user_2=higher_user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DirectConversation.objects.create(
                    user_1=lower_user,
                    user_2=higher_user,
                )

        self.assertEqual(
            DirectConversation.objects.count(),
            1,
        )


class GroupMembershipModelConstraintTests(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )

        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password="Strong-Test-Password!123",
        )

        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password="Strong-Test-Password!123",
        )

        self.group = GroupConversation.objects.create(
            name="Test Group",
        )

    def test_duplicate_membership_is_rejected(self):
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.MEMBER,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupMembership.objects.create(
                    group=self.group,
                    user=self.alice,
                    role=GroupMembership.Role.MEMBER,
                )

        self.assertEqual(
            GroupMembership.objects.count(),
            1,
        )

    def test_multiple_members_are_allowed(self):
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.MEMBER,
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=GroupMembership.Role.MEMBER,
        )

        self.assertEqual(
            GroupMembership.objects.count(),
            2,
        )

    def test_single_owner_is_allowed(self):
        membership = GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )

        self.assertEqual(
            membership.role,
            GroupMembership.Role.OWNER,
        )

    def test_second_owner_is_rejected(self):
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroupMembership.objects.create(
                    group=self.group,
                    user=self.bob,
                    role=GroupMembership.Role.OWNER,
                )

        self.assertEqual(
            GroupMembership.objects.filter(
                role=GroupMembership.Role.OWNER,
            ).count(),
            1,
        )

    def test_different_groups_can_have_different_owners(self):
        second_group = GroupConversation.objects.create(
            name="Second Group",
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )

        GroupMembership.objects.create(
            group=second_group,
            user=self.bob,
            role=GroupMembership.Role.OWNER,
        )

        self.assertEqual(
            GroupMembership.objects.filter(
                role=GroupMembership.Role.OWNER,
            ).count(),
            2,
        )
