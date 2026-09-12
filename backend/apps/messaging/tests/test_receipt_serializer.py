from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.conversations.models import (
    DirectConversation,
)
from apps.friendships.models import Friendship
from apps.messaging.services import (
    MessageReceiptService,
    MessageService,
)


User = get_user_model()


class MessageReceiptSerializerTests(APITestCase):

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

    def test_message_rest_output_contains_persistent_receipts(self):
        message = (
            MessageService.create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="hello",
            )
        )

        MessageReceiptService.mark_delivered(
            current_user=self.bob,
            message_id=message.pk,
        )

        self.client.force_authenticate(
            user=self.alice
        )

        response = self.client.get(
            f"/api/v1/messages/{message.pk}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            len(response.data["receipts"]),
            1,
        )
        self.assertEqual(
            response.data["receipts"][0][
                "user"
            ]["id"],
            self.bob.pk,
        )
        self.assertIsNotNone(
            response.data["receipts"][0][
                "delivered_at"
            ]
        )
