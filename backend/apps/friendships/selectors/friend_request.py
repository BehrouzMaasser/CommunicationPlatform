from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.friendships.models import FriendRequest


User = get_user_model()


class FriendRequestSelector:

    @staticmethod
    def list_incoming(*, user: User) -> QuerySet[FriendRequest]:

        return (
            FriendRequest.objects
            .filter(recipient=user)
            .select_related(
                "sender",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-pk",
            )
        )

    @staticmethod
    def list_outgoing(
        *,
        user: User,
    ) -> QuerySet[FriendRequest]:
        return (
            FriendRequest.objects
            .filter(sender=user)
            .select_related(
                "sender",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-pk",
            )
        )

    @staticmethod
    def pending_exists_between_users(
        *,
        user_a: User,
        user_b: User,
    ) -> bool:
        return FriendRequest.objects.filter(
            Q(
                sender=user_a,
                recipient=user_b,
            )
            | Q(
                sender=user_b,
                recipient=user_a,
            )
        ).exists()
