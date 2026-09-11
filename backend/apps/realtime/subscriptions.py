from django.db.models import Q

from apps.conversations.models import (
    DirectConversation,
    GroupMembership,
)


class RealtimeSubscriptionSelector:

    @staticmethod
    def can_access_direct_conversation(
        *,
        user_id: int,
        conversation_id: int,
    ) -> bool:
        return (
            DirectConversation.objects
            .filter(pk=conversation_id)
            .filter(
                Q(user_1_id=user_id)
                | Q(user_2_id=user_id)
            )
            .exists()
        )

    @staticmethod
    def can_access_group(
        *,
        user_id: int,
        group_id: int,
    ) -> bool:
        return (
            GroupMembership.objects
            .filter(
                group_id=group_id,
                user_id=user_id,
            )
            .exists()
        )

    @classmethod
    def can_subscribe(
        cls,
        *,
        user_id: int,
        conversation_type: str,
        conversation_id: int,
    ) -> bool:
        if conversation_type == "dm":
            return (
                cls
                .can_access_direct_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
            )

        if conversation_type == "group":
            return cls.can_access_group(
                user_id=user_id,
                group_id=conversation_id,
            )

        return False
