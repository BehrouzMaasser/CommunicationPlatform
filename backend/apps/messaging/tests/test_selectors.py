from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService
from apps.messaging.models import Message
from apps.messaging.selectors import MessageSelector
from apps.messaging.services import MessageService

from apps.messaging.api.v1.serializers import MessageSerializer


User = get_user_model()


class MessageSelectorTests(TestCase):
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

    def test_list_for_direct_conversation_returns_only_direct_messages(self):
        first = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="First DM",
        )

        second = MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=self.direct_conversation.pk,
            content="Second DM",
        )

        MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        messages = list(
            MessageSelector.list_for_direct_conversation(
                conversation=self.direct_conversation,
            )
        )

        self.assertEqual(
            messages,
            [first, second],
        )

    def test_list_for_group_returns_only_group_messages(self):
        first = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="First group message",
        )

        second = MessageService.create_text_message(
            current_user=self.bob,
            group_id=self.group.pk,
            content="Second group message",
        )

        MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        messages = list(
            MessageSelector.list_for_group(
                group=self.group,
            )
        )

        self.assertEqual(
            messages,
            [first, second],
        )

    def test_direct_history_is_ordered_oldest_first(self):
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

        earlier = timezone.now() - timedelta(hours=2)
        later = timezone.now() - timedelta(hours=1)

        Message.objects.filter(
            pk=first.pk,
        ).update(created_at=earlier)

        Message.objects.filter(
            pk=second.pk,
        ).update(created_at=later)

        messages = list(
            MessageSelector.list_for_direct_conversation(
                conversation=self.direct_conversation,
            )
        )

        self.assertEqual(
            messages,
            [first, second],
        )

    def test_group_history_is_ordered_oldest_first(self):
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

        earlier = timezone.now() - timedelta(hours=2)
        later = timezone.now() - timedelta(hours=1)

        Message.objects.filter(
            pk=first.pk,
        ).update(created_at=earlier)

        Message.objects.filter(
            pk=second.pk,
        ).update(created_at=later)

        messages = list(
            MessageSelector.list_for_group(
                group=self.group,
            )
        )

        self.assertEqual(
            messages,
            [first, second],
        )

    def test_get_for_user_returns_direct_message_for_participant(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        result = MessageSelector.get_for_user(
            user=self.bob,
            message_id=message.pk,
        )

        self.assertEqual(
            result,
            message,
        )

    def test_get_for_user_returns_none_for_direct_message_outsider(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        result = MessageSelector.get_for_user(
            user=self.charlie,
            message_id=message.pk,
        )

        self.assertIsNone(result)

    def test_get_for_user_returns_group_message_for_member(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        result = MessageSelector.get_for_user(
            user=self.bob,
            message_id=message.pk,
        )

        self.assertEqual(
            result,
            message,
        )

    def test_get_for_user_returns_none_for_group_outsider(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        result = MessageSelector.get_for_user(
            user=self.charlie,
            message_id=message.pk,
        )

        self.assertIsNone(result)

    def test_get_for_user_returns_none_for_former_group_member(self):
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

        result = MessageSelector.get_for_user(
            user=self.bob,
            message_id=message.pk,
        )

        self.assertIsNone(result)

    def test_get_for_user_still_returns_dm_after_unfriending(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        result = MessageSelector.get_for_user(
            user=self.bob,
            message_id=message.pk,
        )

        self.assertEqual(
            result,
            message,
        )

    def test_get_for_user_returns_none_for_unknown_message(self):
        result = MessageSelector.get_for_user(
            user=self.alice,
            message_id=999999,
        )

        self.assertIsNone(result)

    def test_reply_relationship_is_loaded_and_accessible(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Parent",
        )

        reply = MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=self.direct_conversation.pk,
            content="Reply",
            reply_to_id=parent.pk,
        )

        result = MessageSelector.get_for_user(
            user=self.alice,
            message_id=reply.pk,
        )

        self.assertEqual(
            result.reply_to,
            parent,
        )
        self.assertEqual(
            result.reply_to.sender,
            self.alice,
        )

    def test_selected_messages_serialize_without_additional_queries(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Parent",
        )

        MessageService.create_text_message(
            current_user=self.bob,
            direct_conversation_id=self.direct_conversation.pk,
            content="Reply",
            reply_to_id=parent.pk,
        )

        messages = list(
            MessageSelector.list_for_direct_conversation(
                conversation=self.direct_conversation,
            )
        )

        with self.assertNumQueries(0):
            data = MessageSerializer(
                messages,
                many=True,
            ).data

        self.assertEqual(len(data), 2)
