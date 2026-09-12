from django.db.models import Q

from apps.conversations.models import (
    DirectConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship


class RealtimeEphemeralSelector:
    """
    Read-only authorization/audience rules for ephemeral realtime state.
    """

    @staticmethod
    def friend_user_ids(
        *,
        user_id: int,
    ) -> list[int]:
        pairs = list(
            Friendship.objects
            .filter(
                Q(user_1_id=user_id)
                | Q(user_2_id=user_id)
            )
            .values_list(
                "user_1_id",
                "user_2_id",
            )
        )

        return [
            user_2_id
            if user_1_id == user_id
            else user_1_id
            for user_1_id, user_2_id
            in pairs
        ]

    @staticmethod
    def can_publish_typing(
        *,
        user_id: int,
        conversation_type: str,
        conversation_id: int,
    ) -> bool:
        if conversation_type == "dm":
            conversation = (
                DirectConversation.objects
                .filter(pk=conversation_id)
                .filter(
                    Q(user_1_id=user_id)
                    | Q(user_2_id=user_id)
                )
                .first()
            )

            if conversation is None:
                return False

            other_user_id = (
                conversation.user_2_id
                if
                conversation.user_1_id
                == user_id
                else
                conversation.user_1_id
            )

            return Friendship.objects.filter(
                Q(
                    user_1_id=user_id,
                    user_2_id=other_user_id,
                )
                | Q(
                    user_1_id=other_user_id,
                    user_2_id=user_id,
                )
            ).exists()

        if conversation_type == "group":
            return (
                GroupMembership.objects
                .filter(
                    group_id=conversation_id,
                    user_id=user_id,
                )
                .exists()
            )

        return False
