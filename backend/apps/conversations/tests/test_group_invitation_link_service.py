from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.exceptions import (
    GroupInvitationLinkNotFound,
    GroupOwnerRequired,
    InvalidGroupInvitationLink,
)
from apps.conversations.models import (
    GroupInvitation,
    GroupInvitationLink,
    GroupMembership,
)
from apps.conversations.services import (
    GroupConversationService,
    GroupInvitationLinkService,
    GroupInvitationService,
)
from apps.friendships.services import FriendshipService


User = get_user_model()


class GroupInvitationLinkServiceTests(TestCase):
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

    def test_owner_can_create_invitation_link(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.assertTrue(token)
        self.assertEqual(
            link.group,
            self.group,
        )
        self.assertEqual(
            link.created_by,
            self.alice,
        )

        self.assertNotEqual(
            link.token_hash,
            token,
        )

        self.assertEqual(
            link.token_hash,
            GroupInvitationLinkService._hash_token(token),
        )

    def test_raw_token_is_not_stored_in_database(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        link.refresh_from_db()

        self.assertNotEqual(
            link.token_hash,
            token,
        )

        self.assertFalse(
            GroupInvitationLink.objects.filter(
                token_hash=token,
            ).exists()
        )

    def test_non_owner_cannot_create_invitation_link(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        with self.assertRaises(GroupOwnerRequired):
            GroupInvitationLinkService.create_link(
                current_user=self.bob,
                group_id=self.group.pk,
            )

    def test_valid_token_allows_non_friend_to_join(self):
        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        membership, created = (
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )
        )

        self.assertTrue(created)
        self.assertEqual(
            membership.user,
            self.bob,
        )
        self.assertEqual(
            membership.role,
            GroupMembership.Role.MEMBER,
        )

    def test_join_with_token_locks_group_before_link(self):
        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        original_group_lock = (
            GroupConversationService._get_group_for_update
        )
        original_link_lock = (
            GroupInvitationLinkService._get_link_for_update
        )
        lock_order = []

        def lock_group(*, group_id):
            lock_order.append("group")
            return original_group_lock(group_id=group_id)

        def lock_link(*, token_hash, group_id):
            lock_order.append("link")
            return original_link_lock(
                token_hash=token_hash,
                group_id=group_id,
            )

        with (
            patch.object(
                GroupConversationService,
                "_get_group_for_update",
                side_effect=lock_group,
            ),
            patch.object(
                GroupInvitationLinkService,
                "_get_link_for_update",
                side_effect=lock_link,
            ),
        ):
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )

        self.assertEqual(
            lock_order,
            ["group", "link"],
        )

    def test_joining_with_link_is_idempotent_for_existing_member(self):
        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        first_membership, first_created = (
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )
        )

        second_membership, second_created = (
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(
            first_membership,
            second_membership,
        )

        self.assertEqual(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).count(),
            1,
        )

    def test_successful_link_join_removes_pending_direct_invitation(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        GroupInvitationLinkService.join_with_token(
            current_user=self.bob,
            token=token,
        )

        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(InvalidGroupInvitationLink):
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token="not-a-valid-token",
            )

    def test_expired_token_is_rejected(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        GroupInvitationLink.objects.filter(
            pk=link.pk,
        ).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        with self.assertRaises(InvalidGroupInvitationLink):
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

    def test_revoked_token_is_rejected(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        GroupInvitationLinkService.revoke_link(
            current_user=self.alice,
            group_id=self.group.pk,
            link_id=link.pk,
        )

        with self.assertRaises(InvalidGroupInvitationLink):
            GroupInvitationLinkService.join_with_token(
                current_user=self.bob,
                token=token,
            )

    def test_owner_can_revoke_link(self):
        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        revoked = GroupInvitationLinkService.revoke_link(
            current_user=self.alice,
            group_id=self.group.pk,
            link_id=link.pk,
        )

        self.assertIsNotNone(
            revoked.revoked_at,
        )

    def test_revoke_is_idempotent(self):
        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        first = GroupInvitationLinkService.revoke_link(
            current_user=self.alice,
            group_id=self.group.pk,
            link_id=link.pk,
        )

        first_revoked_at = first.revoked_at

        second = GroupInvitationLinkService.revoke_link(
            current_user=self.alice,
            group_id=self.group.pk,
            link_id=link.pk,
        )

        self.assertEqual(
            second.revoked_at,
            first_revoked_at,
        )

    def test_non_owner_cannot_revoke_link(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        with self.assertRaises(GroupOwnerRequired):
            GroupInvitationLinkService.revoke_link(
                current_user=self.bob,
                group_id=self.group.pk,
                link_id=link.pk,
            )

    def test_revoking_unknown_link_raises(self):
        with self.assertRaises(GroupInvitationLinkNotFound):
            GroupInvitationLinkService.revoke_link(
                current_user=self.alice,
                group_id=self.group.pk,
                link_id=999999,
            )
