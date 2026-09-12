from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.conversations.models import (
    GroupMembership,
)
from apps.messaging.exceptions import (
    MessageNotFound,
)
from apps.messaging.models import (
    Message,
    MessageReceipt,
)
from apps.messaging.realtime import (
    MessageReceiptRealtimePublisher,
)
from apps.messaging.selectors import (
    MessageSelector,
)


User = get_user_model()


class MessageReceiptService:

    @staticmethod
    def initialize_for_message(
        *,
        message: Message,
    ) -> None:
        """
        Freeze the recipient set at send time.

        Direct message:
            the other participant

        Group message:
            every current member except the sender

        This runs inside the same transaction that creates the message.
        """
        if (
            message.direct_conversation_id
            is not None
        ):
            conversation = (
                message.direct_conversation
            )

            recipient_ids = {
                conversation.user_1_id,
                conversation.user_2_id,
            }
            recipient_ids.discard(
                message.sender_id
            )
        else:
            recipient_ids = set(
                GroupMembership.objects
                .filter(
                    group_id=(
                        message
                        .group_conversation_id
                    )
                )
                .exclude(
                    user_id=message.sender_id
                )
                .values_list(
                    "user_id",
                    flat=True,
                )
            )

        MessageReceipt.objects.bulk_create(
            [
                MessageReceipt(
                    message=message,
                    user_id=user_id,
                )
                for user_id
                in recipient_ids
            ]
        )

    @staticmethod
    def _get_accessible_message(
        *,
        current_user: User,
        message_id: int,
    ) -> Message:
        message = (
            MessageSelector.get_for_user(
                user=current_user,
                message_id=message_id,
            )
        )

        if message is None:
            raise MessageNotFound

        return message

    @staticmethod
    def _same_context_filter(
        *,
        message: Message,
    ) -> Q:
        if (
            message.direct_conversation_id
            is not None
        ):
            return Q(
                message__direct_conversation_id=(
                    message
                    .direct_conversation_id
                ),
                message__group_conversation__isnull=True,
            )

        return Q(
            message__direct_conversation__isnull=True,
            message__group_conversation_id=(
                message
                .group_conversation_id
            ),
        )

    @classmethod
    def mark_delivered(
        cls,
        *,
        current_user: User,
        message_id: int,
    ) -> MessageReceipt | None:
        with transaction.atomic():
            message = (
                cls._get_accessible_message(
                    current_user=current_user,
                    message_id=message_id,
                )
            )

            receipt = (
                MessageReceipt.objects
                .select_for_update()
                .filter(
                    message=message,
                    user=current_user,
                )
                .first()
            )

            # Sender, later group joiner, or otherwise not an original
            # recipient: there is nothing to acknowledge.
            if receipt is None:
                return None

            if (
                receipt.delivered_at
                is not None
            ):
                return receipt

            delivered_at = timezone.now()

            receipt.delivered_at = (
                delivered_at
            )
            receipt.save(
                update_fields=[
                    "delivered_at",
                ]
            )

            (
                MessageReceiptRealtimePublisher
                .delivered_after_commit(
                    message=message,
                    user_id=current_user.pk,
                    delivered_at=delivered_at,
                )
            )

            return receipt

    @classmethod
    def mark_read_through(
        cls,
        *,
        current_user: User,
        message_id: int,
    ) -> int:
        """
        Mark every original-recipient receipt for current_user as read through
        the supplied message position in that conversation.

        The target may be the user's own message; it acts as a conversation
        watermark, while only existing receipt rows are updated.
        """
        with transaction.atomic():
            target = (
                cls._get_accessible_message(
                    current_user=current_user,
                    message_id=message_id,
                )
            )

            receipts = list(
                MessageReceipt.objects
                .select_for_update()
                .filter(
                    user=current_user,
                )
                .filter(
                    cls._same_context_filter(
                        message=target,
                    )
                )
                .filter(
                    Q(
                        message__created_at__lt=(
                            target.created_at
                        )
                    )
                    | Q(
                        message__created_at=(
                            target.created_at
                        ),
                        message_id__lte=target.pk,
                    )
                )
                .filter(
                    read_at__isnull=True,
                )
                .select_related(
                    "message",
                )
            )

            if not receipts:
                return 0

            read_at = timezone.now()

            for receipt in receipts:
                if (
                    receipt.delivered_at
                    is None
                ):
                    receipt.delivered_at = (
                        read_at
                    )

                receipt.read_at = read_at

            MessageReceipt.objects.bulk_update(
                receipts,
                [
                    "delivered_at",
                    "read_at",
                ],
            )

            (
                MessageReceiptRealtimePublisher
                .read_after_commit(
                    message=target,
                    user_id=current_user.pk,
                    read_at=read_at,
                )
            )

            return len(receipts)
