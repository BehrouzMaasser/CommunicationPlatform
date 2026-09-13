from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.messaging.models import (
    MessageReceipt,
)
from apps.messaging.services import (
    MessageReceiptService,
    MessageService,
)


User = get_user_model()


class MessageReceiptServiceTests(TestCase):

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

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )

        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.dm = DirectConversation.objects.create(
            user_1=low,
            user_2=high,
        )

    def test_direct_message_freezes_other_participant_as_recipient(self):
        message = (
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="hello",
            )
        )

        receipts = list(
            MessageReceipt.objects
            .filter(message=message)
            .values_list(
                "user_id",
                flat=True,
            )
        )

        self.assertEqual(
            receipts,
            [self.bob.pk],
        )

    def test_group_message_freezes_current_members_except_sender(self):
        group = GroupConversation.objects.create(
            name="Study Group"
        )

        for user, role in [
            (
                self.alice,
                GroupMembership.Role.OWNER,
            ),
            (
                self.bob,
                GroupMembership.Role.MEMBER,
            ),
        ]:
            GroupMembership.objects.create(
                group=group,
                user=user,
                role=role,
            )

        message = (
            MessageService.create_text_message(
                current_user=self.alice,
                group_id=group.pk,
                content="hello group",
            )
        )

        # Charlie joins AFTER message creation.
        GroupMembership.objects.create(
            group=group,
            user=self.charlie,
            role=(
                GroupMembership.Role.MEMBER
            ),
        )

        receipt_ids = set(
            MessageReceipt.objects
            .filter(message=message)
            .values_list(
                "user_id",
                flat=True,
            )
        )

        self.assertEqual(
            receipt_ids,
            {self.bob.pk},
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher."
        "publish_after_commit"
    )
    def test_delivery_is_idempotent(
        self,
        publish,
    ):
        message = (
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="hello",
            )
        )

        publish.reset_mock()

        MessageReceiptService.mark_delivered(
            current_user=self.bob,
            message_id=message.pk,
        )
        MessageReceiptService.mark_delivered(
            current_user=self.bob,
            message_id=message.pk,
        )

        receipt = MessageReceipt.objects.get(
            message=message,
            user=self.bob,
        )

        self.assertIsNotNone(
            receipt.delivered_at
        )

        delivery_calls = [
            call
            for call
            in publish.call_args_list
            if (
                call.kwargs[
                    "event_type"
                ].value
                == "message.delivered"
            )
        ]

        self.assertEqual(
            len(delivery_calls),
            1,
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher."
        "publish_after_commit"
    )
    def test_read_through_marks_all_older_recipient_receipts(
        self,
        publish,
    ):
        first = (
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="one",
            )
        )

        second = (
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="two",
            )
        )

        # Latest message is Bob's own message. It still works as a read
        # watermark for Alice's older messages.
        latest = (
            MessageService.create_text_message(
                current_user=self.bob,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="reply",
            )
        )

        publish.reset_mock()

        updated = (
            MessageReceiptService
            .mark_read_through(
                current_user=self.bob,
                message_id=latest.pk,
            )
        )

        self.assertEqual(
            updated,
            2,
        )

        for message in [
            first,
            second,
        ]:
            receipt = (
                MessageReceipt.objects.get(
                    message=message,
                    user=self.bob,
                )
            )

            self.assertIsNotNone(
                receipt.delivered_at
            )
            self.assertIsNotNone(
                receipt.read_at
            )

        read_calls = [
            call
            for call
            in publish.call_args_list
            if (
                call.kwargs[
                    "event_type"
                ].value
                == "message.read"
            )
        ]

        self.assertEqual(
            len(read_calls),
            1,
        )

        self.assertEqual(
            read_calls[0]
            .kwargs["payload"][
                "message_id"
            ],
            latest.pk,
        )

        self.assertEqual(
            read_calls[0]
            .kwargs["payload"][
                "read_count"
            ],
            2,
        )

        self.assertCountEqual(
            read_calls[0]
            .kwargs["group_names"],
            [
                f"dm.{self.dm.pk}",
                f"user.{self.bob.pk}",
            ],
        )
