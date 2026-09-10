from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService
from apps.messaging.exceptions import (
    InvalidMessageContent,
    InvalidMessageContext,
    MessageContextNotFound,
    ReplyMessageNotFound,
)
from apps.messaging.models import Message
from apps.messaging.services import MessageService


User = get_user_model()


class MessageServiceTests(TestCase):
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

    def test_participant_can_send_direct_text_message(self):
        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Hello Bob",
        )

        self.assertEqual(
            message.sender,
            self.alice,
        )
        self.assertEqual(
            message.direct_conversation,
            self.direct_conversation,
        )
        self.assertIsNone(
            message.group_conversation,
        )
        self.assertEqual(
            message.content,
            "Hello Bob",
        )

    def test_direct_message_can_be_sent_after_unfriending(self):
        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Existing DM still works",
        )

        self.assertEqual(
            message.direct_conversation,
            self.direct_conversation,
        )

    def test_non_participant_cannot_send_direct_message(self):
        with self.assertRaises(MessageContextNotFound):
            MessageService.create_text_message(
                current_user=self.charlie,
                direct_conversation_id=self.direct_conversation.pk,
                content="Unauthorized",
            )

        self.assertFalse(
            Message.objects.filter(
                sender=self.charlie,
            ).exists()
        )

    def test_group_member_can_send_message(self):
        message = MessageService.create_text_message(
            current_user=self.bob,
            group_id=self.group.pk,
            content="Hello group",
        )

        self.assertEqual(
            message.sender,
            self.bob,
        )
        self.assertEqual(
            message.group_conversation,
            self.group,
        )

    def test_non_member_cannot_send_group_message(self):
        with self.assertRaises(MessageContextNotFound):
            MessageService.create_text_message(
                current_user=self.charlie,
                group_id=self.group.pk,
                content="Unauthorized",
            )

        self.assertFalse(
            Message.objects.filter(
                sender=self.charlie,
            ).exists()
        )

    def test_removed_member_cannot_send_group_message(self):
        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        with self.assertRaises(MessageContextNotFound):
            MessageService.create_text_message(
                current_user=self.bob,
                group_id=self.group.pk,
                content="I should no longer be able to send",
            )

    def test_missing_context_is_rejected(self):
        with self.assertRaises(InvalidMessageContext):
            MessageService.create_text_message(
                current_user=self.alice,
                content="Missing context",
            )

    def test_both_contexts_are_rejected(self):
        with self.assertRaises(InvalidMessageContext):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                group_id=self.group.pk,
                content="Too many contexts",
            )

    def test_unknown_direct_conversation_is_not_accessible(self):
        with self.assertRaises(MessageContextNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=999999,
                content="Unknown",
            )

    def test_unknown_group_is_not_accessible(self):
        with self.assertRaises(MessageContextNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                group_id=999999,
                content="Unknown",
            )

    def test_empty_text_is_rejected(self):
        with self.assertRaises(InvalidMessageContent):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content="",
            )

    def test_whitespace_only_text_is_rejected(self):
        with self.assertRaises(InvalidMessageContent):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content="   \t\n   ",
            )

    def test_non_string_text_is_rejected(self):
        with self.assertRaises(InvalidMessageContent):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content=None,
            )

    def test_text_is_stored_exactly_as_supplied(self):
        content = "  Hello Bob  "

        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content=content,
        )

        self.assertEqual(
            message.content,
            content,
        )

    def test_direct_conversation_last_activity_is_updated(self):
        previous_activity = self.direct_conversation.last_activity_at

        message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Activity update",
        )

        self.direct_conversation.refresh_from_db()

        self.assertEqual(
            self.direct_conversation.last_activity_at,
            message.created_at,
        )
        self.assertGreaterEqual(
            self.direct_conversation.last_activity_at,
            previous_activity,
        )

    def test_group_last_activity_is_updated(self):
        previous_activity = self.group.last_activity_at

        message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Activity update",
        )

        self.group.refresh_from_db()

        self.assertEqual(
            self.group.last_activity_at,
            message.created_at,
        )
        self.assertGreaterEqual(
            self.group.last_activity_at,
            previous_activity,
        )

    def test_reply_within_same_direct_conversation_is_allowed(self):
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

        self.assertEqual(
            reply.reply_to,
            parent,
        )

    def test_nested_reply_is_allowed(self):
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

        third = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="Third",
            reply_to_id=second.pk,
        )

        self.assertEqual(
            third.reply_to,
            second,
        )

    def test_reply_within_same_group_is_allowed(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Parent",
        )

        reply = MessageService.create_text_message(
            current_user=self.bob,
            group_id=self.group.pk,
            content="Reply",
            reply_to_id=parent.pk,
        )

        self.assertEqual(
            reply.reply_to,
            parent,
        )

    def test_direct_message_cannot_reply_to_group_message(self):
        group_message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        with self.assertRaises(ReplyMessageNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content="Cross-context reply",
                reply_to_id=group_message.pk,
            )

    def test_group_message_cannot_reply_to_direct_message(self):
        direct_message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.direct_conversation.pk,
            content="DM",
        )

        with self.assertRaises(ReplyMessageNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                group_id=self.group.pk,
                content="Cross-context reply",
                reply_to_id=direct_message.pk,
            )

    def test_reply_to_unknown_message_is_rejected(self):
        with self.assertRaises(ReplyMessageNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content="Reply",
                reply_to_id=999999,
            )

    def test_failed_reply_creation_does_not_update_last_activity(self):
        previous_activity = self.direct_conversation.last_activity_at

        with self.assertRaises(ReplyMessageNotFound):
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=self.direct_conversation.pk,
                content="Invalid reply",
                reply_to_id=999999,
            )

        self.direct_conversation.refresh_from_db()

        self.assertEqual(
            self.direct_conversation.last_activity_at,
            previous_activity,
        )
