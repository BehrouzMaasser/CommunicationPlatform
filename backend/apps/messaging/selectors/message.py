from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
)
from apps.messaging.models import Message


User = get_user_model()


class MessageSelector:

    @staticmethod
    def _base_queryset() -> QuerySet[Message]:
        return (
            Message.objects
            .select_related(
                "sender",
                "reply_to",
                "reply_to__sender",
                "direct_conversation",
                "group_conversation",
            )
            .prefetch_related(
                "receipts",
                "receipts__user",
            )
        )

    @classmethod
    def list_for_direct_conversation(
        cls,
        *,
        conversation: DirectConversation,
    ) -> QuerySet[Message]:
        return (
            cls._base_queryset()
            .filter(
                direct_conversation=conversation,
                group_conversation__isnull=True,
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

    @classmethod
    def list_for_group(
        cls,
        *,
        group: GroupConversation,
    ) -> QuerySet[Message]:
        return (
            cls._base_queryset()
            .filter(
                direct_conversation__isnull=True,
                group_conversation=group,
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

    @classmethod
    def get_for_user(
        cls,
        *,
        user: User,
        message_id: int,
    ) -> Message | None:
        return (
            cls._base_queryset()
            .filter(pk=message_id)
            .filter(
                Q(
                    direct_conversation__user_1=user,
                )
                | Q(
                    direct_conversation__user_2=user,
                )
                | Q(
                    group_conversation__memberships__user=user,
                )
            )
            .distinct()
            .first()
        )
