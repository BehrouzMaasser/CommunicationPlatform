from typing import Union

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.friendships.models import Friendship


User = get_user_model()


class FriendshipSelector:

    @staticmethod
    def exists_between_users(*, user_a: User, user_b: User) -> bool:

        if user_a.pk == user_b.pk:
            return False

        user_1_id , user_2_id = sorted((user_a.pk, user_b.pk))

        return Friendship.objects.filter(user_1_id=user_1_id, user_2_id=user_2_id).exists()

    @staticmethod
    def get_between_users(*, user_a: User, user_b: User) -> Union[Friendship, None]:

        if user_a.pk == user_b.pk:
            return None

        user_1_id , user_2_id = sorted((user_a.pk, user_b.pk))

        return (
            Friendship.objects
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

    @staticmethod
    def list_for_user(*, user: User) -> QuerySet[Friendship]:

        return (
            Friendship.objects
            .filter(
                Q(user_1=user) | Q(user_2=user)
            )
            .select_related(
                "user_1",
                "user_2",
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

    @staticmethod
    def list_friend_users(*, user: User) -> QuerySet[User]:

        friends_as_user_1 = Friendship.objects.filter(user_2=user).values("user_1_id")
        friends_as_user_2 = Friendship.objects.filter(user_1=user).values("user_2_id")

        return (
            User.objects
            .filter(
                Q(pk__in=friends_as_user_1) | Q(pk__in=friends_as_user_2)
            )
            .order_by(
                "username",
                "pk",
            )
        )
