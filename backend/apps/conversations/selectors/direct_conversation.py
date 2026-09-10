from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.conversations.models import DirectConversation


User = get_user_model()


class DirectConversationSelector:

    @staticmethod
    def list_for_user(
        *,
        user: User,
    ) -> QuerySet[DirectConversation]:
        return (
            DirectConversation.objects
            .filter(
                Q(user_1=user)
                | Q(user_2=user)
            )
            .select_related(
                "user_1",
                "user_2",
            )
            .order_by(
                "-last_activity_at",
                "-pk",
            )
        )

    @staticmethod
    def get_for_user(
        *,
        user: User,
        conversation_id: int,
    ) -> DirectConversation | None:
        return (
            DirectConversation.objects
            .filter(
                Q(user_1=user)
                | Q(user_2=user),
                pk=conversation_id,
            )
            .select_related(
                "user_1",
                "user_2",
            )
            .first()
        )

    @staticmethod
    def get_between_users(
        *,
        user_a: User,
        user_b: User,
    ) -> DirectConversation | None:
        if user_a.pk == user_b.pk:
            return None

        user_1_id = min(
            user_a.pk,
            user_b.pk,
        )
        user_2_id = max(
            user_a.pk,
            user_b.pk,
        )

        return (
            DirectConversation.objects
            .select_related(
                "user_1",
                "user_2",
            )
            .filter(
                user_1_id=user_1_id,
                user_2_id=user_2_id,
            )
            .first()
        )
