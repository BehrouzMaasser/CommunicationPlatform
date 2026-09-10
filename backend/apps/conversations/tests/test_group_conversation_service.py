from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.exceptions import (
    GroupMembershipNotFound,
    GroupNotFound,
    GroupOwnerCannotBeRemoved,
    GroupOwnerRequired,
    InvalidGroupName,
    UserAlreadyGroupMember,
)
from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)
from apps.conversations.services.group_conversation import (
    GroupConversationService,
)


User = get_user_model()


class GroupConversationServiceTests(TestCase):
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

    def test_create_group_creates_owner_membership(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.assertEqual(
            GroupConversation.objects.count(),
            1,
        )

        membership = GroupMembership.objects.get(
            group=group,
            user=self.alice,
        )

        self.assertEqual(
            membership.role,
            GroupMembership.Role.OWNER,
        )

    def test_create_group_rejects_empty_name(self):
        with self.assertRaises(InvalidGroupName):
            GroupConversationService.create_group(
                current_user=self.alice,
                name="",
            )

        self.assertFalse(
            GroupConversation.objects.exists()
        )

    def test_create_group_rejects_whitespace_only_name(self):
        with self.assertRaises(InvalidGroupName):
            GroupConversationService.create_group(
                current_user=self.alice,
                name="   ",
            )

        self.assertFalse(
            GroupConversation.objects.exists()
        )

    def test_add_member_creates_member_membership(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        membership = GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.assertEqual(
            membership.user,
            self.bob,
        )

        self.assertEqual(
            membership.role,
            GroupMembership.Role.MEMBER,
        )

    def test_add_member_rejects_duplicate_membership(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        with self.assertRaises(UserAlreadyGroupMember):
            GroupConversationService._add_member(
                group=group,
                user=self.bob,
            )

    def test_owner_can_rename_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Old Name",
        )

        updated_group = GroupConversationService.rename_group(
            current_user=self.alice,
            group_id=group.pk,
            name="New Name",
        )

        self.assertEqual(
            updated_group.name,
            "New Name",
        )

        group.refresh_from_db()

        self.assertEqual(
            group.name,
            "New Name",
        )

    def test_non_owner_cannot_rename_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        with self.assertRaises(GroupOwnerRequired):
            GroupConversationService.rename_group(
                current_user=self.bob,
                group_id=group.pk,
                name="Unauthorized Rename",
            )

        group.refresh_from_db()

        self.assertEqual(
            group.name,
            "Study Group",
        )

    def test_rename_unknown_group_raises(self):
        with self.assertRaises(GroupNotFound):
            GroupConversationService.rename_group(
                current_user=self.alice,
                group_id=999999,
                name="New Name",
            )

    def test_owner_can_remove_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=group.pk,
            member_user_id=self.bob.pk,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=group,
                user=self.bob,
            ).exists()
        )

    def test_non_owner_cannot_remove_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        GroupConversationService._add_member(
            group=group,
            user=self.charlie,
        )

        with self.assertRaises(GroupOwnerRequired):
            GroupConversationService.remove_member(
                current_user=self.bob,
                group_id=group.pk,
                member_user_id=self.charlie.pk,
            )

        self.assertTrue(
            GroupMembership.objects.filter(
                group=group,
                user=self.charlie,
            ).exists()
        )

    def test_owner_cannot_remove_themselves_as_regular_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        with self.assertRaises(GroupOwnerCannotBeRemoved):
            GroupConversationService.remove_member(
                current_user=self.alice,
                group_id=group.pk,
                member_user_id=self.alice.pk,
            )

        self.assertTrue(
            GroupConversation.objects.filter(
                pk=group.pk,
            ).exists()
        )

    def test_remove_unknown_member_raises(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        with self.assertRaises(GroupMembershipNotFound):
            GroupConversationService.remove_member(
                current_user=self.alice,
                group_id=group.pk,
                member_user_id=self.bob.pk,
            )

    def test_regular_member_can_leave_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        GroupConversationService.leave_group(
            current_user=self.bob,
            group_id=group.pk,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=group,
                user=self.bob,
            ).exists()
        )

        self.assertTrue(
            GroupConversation.objects.filter(
                pk=group.pk,
            ).exists()
        )

    def test_owner_leaving_disbands_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        GroupConversationService.leave_group(
            current_user=self.alice,
            group_id=group.pk,
        )

        self.assertFalse(
            GroupConversation.objects.filter(
                pk=group.pk,
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group_id=group.pk,
            ).exists()
        )

    def test_non_member_cannot_leave_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        with self.assertRaises(GroupMembershipNotFound):
            GroupConversationService.leave_group(
                current_user=self.bob,
                group_id=group.pk,
            )

    def test_owner_can_disband_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        GroupConversationService.disband_group(
            current_user=self.alice,
            group_id=group.pk,
        )

        self.assertFalse(
            GroupConversation.objects.filter(
                pk=group.pk,
            ).exists()
        )

    def test_non_owner_cannot_disband_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        with self.assertRaises(GroupOwnerRequired):
            GroupConversationService.disband_group(
                current_user=self.bob,
                group_id=group.pk,
            )

        self.assertTrue(
            GroupConversation.objects.filter(
                pk=group.pk,
            ).exists()
        )
