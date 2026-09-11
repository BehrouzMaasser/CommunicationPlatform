from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService
from apps.messaging.models import Message
from apps.messaging.services import MessageService


User = get_user_model()


class MessagingApiTestBase(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.client = APIClient()

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

        self.direct_conversation, _ = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

    def login(self, user):
        logged_in = self.client.login(
            email=user.email,
            password=self.PASSWORD,
        )
        self.assertTrue(logged_in)


class MessagingApiAuthenticationTests(MessagingApiTestBase):

    def test_message_endpoints_require_authentication(self):
        endpoints = [
            (
                "get",
                reverse(
                    "dm-message-list-create",
                    kwargs={
                        "conversation_id": self.direct_conversation.pk,
                    },
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "dm-message-list-create",
                    kwargs={
                        "conversation_id": self.direct_conversation.pk,
                    },
                ),
                {"content": "Hello"},
            ),
            (
                "get",
                reverse(
                    "group-message-list-create",
                    kwargs={"group_id": self.group.pk},
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "group-message-list-create",
                    kwargs={"group_id": self.group.pk},
                ),
                {"content": "Hello group"},
            ),
            (
                "get",
                reverse(
                    "message-detail",
                    kwargs={"message_id": 999999},
                ),
                None,
            ),
        ]

        for method, url, data in endpoints:
            with self.subTest(method=method, url=url):
                request_method = getattr(self.client, method)

                if data is None:
                    response = request_method(url)
                else:
                    response = request_method(
                        url,
                        data=data,
                        format="json",
                    )

                self.assertEqual(response.status_code, 401)


class DirectMessageApiTests(MessagingApiTestBase):

    def test_participant_can_create_direct_message(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": "Hello Bob"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(message.sender, self.alice)
        self.assertEqual(
            message.direct_conversation,
            self.direct_conversation,
        )
        self.assertEqual(message.content, "Hello Bob")

    def test_direct_message_response_does_not_expose_email(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": "Hello Bob"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn(
            "email",
            response.data["sender"],
        )

    def test_direct_message_preserves_exact_text(self):
        self.login(self.alice)

        content = "  Hello Bob  "

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": content},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["content"],
            content,
        )

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            message.content,
            content,
        )

    def test_blank_direct_text_returns_400(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": "   \t\n   "},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Message.objects.exists()
        )

    def test_direct_message_send_is_forbidden_after_unfriending(self):
        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": "Blocked after unfriend"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Message.objects.filter(
                sender=self.alice,
                content="Blocked after unfriend",
            ).exists()
        )

    def test_direct_outsider_cannot_send_message(self):
        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {"content": "Unauthorized"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            Message.objects.filter(
                sender=self.charlie,
            ).exists()
        )

    def test_direct_outsider_cannot_list_messages(self):
        MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Private DM",
        )

        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_direct_message_list_is_paginated(self):
        first = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="First",
        )
        second = MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=self.direct_conversation.pk,
            content="Second",
        )

        self.login(self.alice)

        response = self.client.get(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("results", response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [first.pk, second.pk],
        )

    def test_direct_reply_in_same_context_is_created(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Parent",
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {
                "content": "Reply",
                "reply_to_id": parent.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["reply_to"]["id"],
            parent.pk,
        )
        self.assertEqual(
            response.data["reply_to"]["sender"]["id"],
            self.alice.pk,
        )
        self.assertNotIn(
            "email",
            response.data["reply_to"]["sender"],
        )

    def test_direct_reply_serialization_is_shallow(self):
        first = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="First",
        )

        second = MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=self.direct_conversation.pk,
            content="Second",
            reply_to_id=first.pk,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {
                "content": "Third",
                "reply_to_id": second.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["reply_to"]["id"],
            second.pk,
        )
        self.assertNotIn(
            "reply_to",
            response.data["reply_to"],
        )

    def test_direct_message_cannot_reply_to_group_message(self):
        group_message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {
                "content": "Cross-context reply",
                "reply_to_id": group_message.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_reply_target_returns_404(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={
                    "conversation_id": self.direct_conversation.pk,
                },
            ),
            {
                "content": "Reply",
                "reply_to_id": 999999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)


class GroupMessageApiTests(MessagingApiTestBase):

    def test_group_member_can_create_message(self):
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"content": "Hello group"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(message.sender, self.bob)
        self.assertEqual(
            message.group_conversation,
            self.group,
        )

    def test_group_outsider_cannot_send_message(self):
        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"content": "Unauthorized"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_former_group_member_cannot_send_message(self):
        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"content": "No longer a member"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_former_group_member_cannot_list_messages(self):
        MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Private group message",
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_group_message_list_is_paginated(self):
        first = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="First",
        )
        second = MessageService.create_text_message(
            current_user=self.bob,
            group_id=self.group.pk,
            content="Second",
        )

        self.login(self.alice)

        response = self.client.get(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [first.pk, second.pk],
        )

    def test_group_reply_in_same_context_is_created(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Parent",
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {
                "content": "Reply",
                "reply_to_id": parent.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["reply_to"]["id"],
            parent.pk,
        )

    def test_group_message_cannot_reply_to_direct_message(self):
        direct_message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {
                "content": "Cross-context reply",
                "reply_to_id": direct_message.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)


class MessageDetailApiTests(MessagingApiTestBase):

    def test_dm_participant_can_get_message_detail(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Private DM",
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], message.pk)
        self.assertNotIn(
            "email",
            response.data["sender"],
        )

    def test_dm_detail_remains_accessible_after_unfriending(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Private DM",
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_dm_outsider_gets_404_for_message_detail(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Private DM",
        )

        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_group_member_can_get_message_detail(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_former_group_member_gets_404_for_message_detail(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_message_returns_404(self):
        self.login(self.alice)

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)
