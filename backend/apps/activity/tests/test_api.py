from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupInvitation,
    GroupMembership,
)
from apps.friendships.models import FriendRequest, Friendship
from apps.messaging.models import MessageReceipt
from apps.messaging.services import MessageService


User = get_user_model()


class ActivitySummaryApiTests(APITestCase):

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password-123",
        )
        self.charlie = User.objects.create_user(
            username="charlie",
            email="charlie@example.com",
            password="password-123",
        )

    def login(self, user):
        self.client.force_authenticate(user=user)

    def test_summary_requires_authentication(self):
        response = self.client.get(
            "/api/v1/activity/summary/"
        )

        self.assertEqual(response.status_code, 401)

    def test_empty_summary(self):
        self.login(self.alice)

        response = self.client.get(
            "/api/v1/activity/summary/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "pending_friend_requests": 0,
                "pending_group_invitations": 0,
                "unread_direct_messages": 0,
                "unread_group_messages": 0,
                "direct_conversations": [],
                "groups": [],
            },
        )

    def test_summary_counts_pending_and_unread_by_conversation(self):
        FriendRequest.objects.create(
            sender=self.charlie,
            recipient=self.alice,
        )

        group = GroupConversation.objects.create(
            name="Study Group",
        )
        GroupMembership.objects.create(
            group=group,
            user=self.bob,
            role=GroupMembership.Role.OWNER,
        )
        GroupMembership.objects.create(
            group=group,
            user=self.alice,
            role=GroupMembership.Role.MEMBER,
        )
        GroupInvitation.objects.create(
            group=group,
            invited_by=self.bob,
            recipient=self.charlie,
        )

        other_group = GroupConversation.objects.create(
            name="Other Group",
        )
        GroupMembership.objects.create(
            group=other_group,
            user=self.bob,
            role=GroupMembership.Role.OWNER,
        )
        GroupInvitation.objects.create(
            group=other_group,
            invited_by=self.bob,
            recipient=self.alice,
        )

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )
        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )
        dm = DirectConversation.objects.create(
            user_1=low,
            user_2=high,
        )

        first_dm = MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=dm.pk,
            content="one",
        )
        MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=dm.pk,
            content="two",
        )
        MessageService.create_text_message(
            current_user=self.bob,
            group_id=group.pk,
            content="group message",
        )

        MessageReceipt.objects.filter(
            message=first_dm,
            user=self.alice,
        ).update(
            delivered_at=timezone.now(),
            read_at=timezone.now(),
        )

        self.login(self.alice)
        response = self.client.get(
            "/api/v1/activity/summary/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["pending_friend_requests"],
            1,
        )
        self.assertEqual(
            response.data["pending_group_invitations"],
            1,
        )
        self.assertEqual(
            response.data["unread_direct_messages"],
            1,
        )
        self.assertEqual(
            response.data["unread_group_messages"],
            1,
        )
        self.assertEqual(
            response.data["direct_conversations"],
            [
                {
                    "conversation_id": dm.pk,
                    "unread_count": 1,
                },
            ],
        )
        self.assertEqual(
            response.data["groups"],
            [
                {
                    "group_id": group.pk,
                    "unread_count": 1,
                },
            ],
        )

    def test_former_group_member_has_no_group_unread_badge(self):
        group = GroupConversation.objects.create(
            name="Study Group",
        )
        GroupMembership.objects.create(
            group=group,
            user=self.bob,
            role=GroupMembership.Role.OWNER,
        )
        membership = GroupMembership.objects.create(
            group=group,
            user=self.alice,
            role=GroupMembership.Role.MEMBER,
        )

        MessageService.create_text_message(
            current_user=self.bob,
            group_id=group.pk,
            content="before removal",
        )

        self.assertTrue(
            MessageReceipt.objects.filter(
                user=self.alice,
                read_at__isnull=True,
            ).exists()
        )

        membership.delete()

        self.login(self.alice)
        response = self.client.get(
            "/api/v1/activity/summary/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["unread_group_messages"],
            0,
        )
        self.assertEqual(
            response.data["groups"],
            [],
        )
