from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
)
from apps.messaging.models import Message


User = get_user_model()


class MessageModelConstraintTests(TestCase):
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

        lower_user, higher_user = sorted(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        self.direct_conversation = DirectConversation.objects.create(
            user_1=lower_user,
            user_2=higher_user,
        )

        self.group = GroupConversation.objects.create(
            name="Study Group",
        )

    def test_message_with_direct_context_is_allowed(self):
        message = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="Hello",
        )

        self.assertEqual(
            message.direct_conversation,
            self.direct_conversation,
        )
        self.assertIsNone(
            message.group_conversation,
        )

    def test_message_with_group_context_is_allowed(self):
        message = Message.objects.create(
            sender=self.alice,
            group_conversation=self.group,
            content="Hello group",
        )

        self.assertEqual(
            message.group_conversation,
            self.group,
        )
        self.assertIsNone(
            message.direct_conversation,
        )

    def test_message_without_context_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    sender=self.alice,
                    content="No context",
                )

        self.assertFalse(
            Message.objects.exists()
        )

    def test_message_with_both_contexts_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    sender=self.alice,
                    direct_conversation=self.direct_conversation,
                    group_conversation=self.group,
                    content="Too many contexts",
                )

        self.assertFalse(
            Message.objects.exists()
        )

    def test_blank_content_is_allowed_at_model_level(self):
        message = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="",
        )

        self.assertEqual(
            message.content,
            "",
        )

    def test_reply_can_reference_another_message(self):
        parent = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="Parent",
        )

        reply = Message.objects.create(
            sender=self.bob,
            direct_conversation=self.direct_conversation,
            content="Reply",
            reply_to=parent,
        )

        self.assertEqual(
            reply.reply_to,
            parent,
        )

    def test_nested_replies_are_allowed(self):
        first = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="First",
        )

        second = Message.objects.create(
            sender=self.bob,
            direct_conversation=self.direct_conversation,
            content="Second",
            reply_to=first,
        )

        third = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="Third",
            reply_to=second,
        )

        self.assertEqual(
            third.reply_to,
            second,
        )
        self.assertEqual(
            third.reply_to.reply_to,
            first,
        )

    def test_deleting_reply_target_sets_reply_to_null(self):
        parent = Message.objects.create(
            sender=self.alice,
            direct_conversation=self.direct_conversation,
            content="Parent",
        )

        reply = Message.objects.create(
            sender=self.bob,
            direct_conversation=self.direct_conversation,
            content="Reply",
            reply_to=parent,
        )

        parent.delete()
        reply.refresh_from_db()

        self.assertIsNone(
            reply.reply_to,
        )
