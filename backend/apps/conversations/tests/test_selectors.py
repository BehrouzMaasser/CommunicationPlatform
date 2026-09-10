from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.models import (
    DirectConversation,
    GroupMembership,
)
from apps.conversations.selectors import (
    DirectConversationSelector,
    GroupConversationSelector,
)
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService


User = get_user_model()


class DirectConversationSelectorTests(TestCase):
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

        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.charlie,
        )

    def test_list_for_user_returns_only_users_conversations(self):
        alice_bob, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        alice_charlie, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.charlie.pk,
        )

        conversations = list(
            DirectConversationSelector.list_for_user(
                user=self.alice,
            )
        )

        self.assertEqual(
            set(conversations),
            {
                alice_bob,
                alice_charlie,
            },
        )

    def test_list_for_user_excludes_unrelated_conversations(self):
        alice_bob, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        FriendshipService._create_friendship(
            user_a=self.bob,
            user_b=self.charlie,
        )

        DirectConversationService.get_or_create(
            current_user=self.bob,
            target_user_id=self.charlie.pk,
        )

        conversations = list(
            DirectConversationSelector.list_for_user(
                user=self.alice,
            )
        )

        self.assertEqual(
            conversations,
            [alice_bob],
        )

    def test_list_for_user_orders_by_last_activity_descending(self):
        older, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        newer, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.charlie.pk,
        )

        old_time = timezone.now() - timedelta(hours=2)
        new_time = timezone.now()

        DirectConversation.objects.filter(
            pk=older.pk,
        ).update(
            last_activity_at=old_time,
        )

        DirectConversation.objects.filter(
            pk=newer.pk,
        ).update(
            last_activity_at=new_time,
        )

        conversations = list(
            DirectConversationSelector.list_for_user(
                user=self.alice,
            )
        )

        self.assertEqual(
            conversations,
            [
                newer,
                older,
            ],
        )

    def test_get_for_user_returns_accessible_conversation(self):
        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        result = DirectConversationSelector.get_for_user(
            user=self.alice,
            conversation_id=conversation.pk,
        )

        self.assertEqual(
            result,
            conversation,
        )

    def test_get_for_user_returns_none_for_non_participant(self):
        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        result = DirectConversationSelector.get_for_user(
            user=self.charlie,
            conversation_id=conversation.pk,
        )

        self.assertIsNone(result)

    def test_get_for_user_returns_none_for_unknown_conversation(self):
        result = DirectConversationSelector.get_for_user(
            user=self.alice,
            conversation_id=999999,
        )

        self.assertIsNone(result)

    def test_get_between_users_returns_conversation_in_either_direction(self):
        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        result = DirectConversationSelector.get_between_users(
            user_a=self.bob,
            user_b=self.alice,
        )

        self.assertEqual(
            result,
            conversation,
        )

    def test_get_between_same_user_returns_none(self):
        result = DirectConversationSelector.get_between_users(
            user_a=self.alice,
            user_b=self.alice,
        )

        self.assertIsNone(result)


class GroupConversationSelectorTests(TestCase):
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

    def test_list_for_user_returns_only_groups_where_user_is_member(self):
        alice_group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Alice Group",
        )

        bob_group = GroupConversationService.create_group(
            current_user=self.bob,
            name="Bob Group",
        )

        GroupConversationService._add_member(
            group=bob_group,
            user=self.alice,
        )

        GroupConversationService.create_group(
            current_user=self.charlie,
            name="Charlie Group",
        )

        groups = list(
            GroupConversationSelector.list_for_user(
                user=self.alice,
            )
        )

        self.assertEqual(
            set(groups),
            {
                alice_group,
                bob_group,
            },
        )

    def test_get_for_member_returns_accessible_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        result = GroupConversationSelector.get_for_member(
            user=self.bob,
            group_id=group.pk,
        )

        self.assertEqual(
            result,
            group,
        )

    def test_get_for_member_returns_none_for_non_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        result = GroupConversationSelector.get_for_member(
            user=self.bob,
            group_id=group.pk,
        )

        self.assertIsNone(result)

    def test_get_for_member_returns_none_for_unknown_group(self):
        result = GroupConversationSelector.get_for_member(
            user=self.alice,
            group_id=999999,
        )

        self.assertIsNone(result)

    def test_list_members_returns_group_members(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        memberships = list(
            GroupConversationSelector.list_members(
                group=group,
            )
        )

        self.assertEqual(
            len(memberships),
            2,
        )

        self.assertEqual(
            {
                membership.user
                for membership in memberships
            },
            {
                self.alice,
                self.bob,
            },
        )

    def test_get_membership_returns_membership(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        membership = GroupConversationSelector.get_membership(
            group=group,
            user=self.alice,
        )

        self.assertIsNotNone(membership)

        self.assertEqual(
            membership.role,
            GroupMembership.Role.OWNER,
        )

    def test_get_membership_returns_none_for_non_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        membership = GroupConversationSelector.get_membership(
            group=group,
            user=self.bob,
        )

        self.assertIsNone(membership)

    def test_is_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.assertTrue(
            GroupConversationSelector.is_member(
                group=group,
                user=self.bob,
            )
        )

        self.assertFalse(
            GroupConversationSelector.is_member(
                group=group,
                user=self.charlie,
            )
        )

    def test_is_owner(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.assertTrue(
            GroupConversationSelector.is_owner(
                group=group,
                user=self.alice,
            )
        )

        self.assertFalse(
            GroupConversationSelector.is_owner(
                group=group,
                user=self.bob,
            )
        )
