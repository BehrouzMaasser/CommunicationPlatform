from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.exceptions import (
    FriendshipRequiredForGroupInvitation,
    GroupInvitationAlreadyPending,
    GroupInvitationNotFound,
    GroupInvitationRecipientRequired,
    GroupOwnerRequired,
    UserAlreadyGroupMember,
)
from apps.conversations.models import (
    GroupInvitation,
    GroupMembership,
)
from apps.conversations.services import (
    GroupConversationService,
    GroupInvitationService,
)
from apps.friendships.services import FriendshipService


User = get_user_model()


class GroupInvitationServiceTests(TestCase):
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

    def make_friends(self, user_a, user_b):
        return FriendshipService._create_friendship(
            user_a=user_a,
            user_b=user_b,
        )

    def test_owner_can_invite_friend(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.assertEqual(
            invitation.group,
            self.group,
        )
        self.assertEqual(
            invitation.invited_by,
            self.alice,
        )
        self.assertEqual(
            invitation.recipient,
            self.bob,
        )

    def test_non_owner_cannot_create_invitation(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )
        self.make_friends(self.bob, self.charlie)

        with self.assertRaises(GroupOwnerRequired):
            GroupInvitationService.create_invitation(
                current_user=self.bob,
                group_id=self.group.pk,
                target_user_id=self.charlie.pk,
            )

        self.assertFalse(
            GroupInvitation.objects.exists()
        )

    def test_owner_cannot_invite_non_friend(self):
        with self.assertRaises(
            FriendshipRequiredForGroupInvitation
        ):
            GroupInvitationService.create_invitation(
                current_user=self.alice,
                group_id=self.group.pk,
                target_user_id=self.bob.pk,
            )

        self.assertFalse(
            GroupInvitation.objects.exists()
        )

    def test_owner_cannot_invite_existing_member(self):
        self.make_friends(self.alice, self.bob)

        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        with self.assertRaises(UserAlreadyGroupMember):
            GroupInvitationService.create_invitation(
                current_user=self.alice,
                group_id=self.group.pk,
                target_user_id=self.bob.pk,
            )

    def test_duplicate_pending_invitation_is_rejected(self):
        self.make_friends(self.alice, self.bob)

        GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        with self.assertRaises(
            GroupInvitationAlreadyPending
        ):
            GroupInvitationService.create_invitation(
                current_user=self.alice,
                group_id=self.group.pk,
                target_user_id=self.bob.pk,
            )

        self.assertEqual(
            GroupInvitation.objects.count(),
            1,
        )

    def test_recipient_can_accept_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        membership = GroupInvitationService.accept_invitation(
            current_user=self.bob,
            invitation_id=invitation.pk,
        )

        self.assertEqual(
            membership.group,
            self.group,
        )
        self.assertEqual(
            membership.user,
            self.bob,
        )
        self.assertEqual(
            membership.role,
            GroupMembership.Role.MEMBER,
        )

        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

    def test_acceptance_does_not_require_friendship_to_still_exist(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        membership = GroupInvitationService.accept_invitation(
            current_user=self.bob,
            invitation_id=invitation.pk,
        )

        self.assertEqual(
            membership.user,
            self.bob,
        )

    def test_non_recipient_cannot_accept_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        with self.assertRaises(
            GroupInvitationRecipientRequired
        ):
            GroupInvitationService.accept_invitation(
                current_user=self.charlie,
                invitation_id=invitation.pk,
            )

        self.assertTrue(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.charlie,
            ).exists()
        )

    def test_recipient_can_reject_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        GroupInvitationService.reject_invitation(
            current_user=self.bob,
            invitation_id=invitation.pk,
        )

        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

    def test_non_recipient_cannot_reject_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        with self.assertRaises(
            GroupInvitationRecipientRequired
        ):
            GroupInvitationService.reject_invitation(
                current_user=self.charlie,
                invitation_id=invitation.pk,
            )

        self.assertTrue(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

    def test_unknown_invitation_raises(self):
        with self.assertRaises(GroupInvitationNotFound):
            GroupInvitationService.accept_invitation(
                current_user=self.bob,
                invitation_id=999999,
            )
