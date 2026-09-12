from django.contrib.auth import get_user_model
from django.db import transaction

from apps.friendships.exceptions import (
    FriendshipNotFound,
    SelfFriendshipNotAllowed,
    UsersAlreadyFriends,
)

from apps.friendships.models import Friendship
from apps.friendships.realtime import FriendshipRealtimePublisher


User = get_user_model()


class FriendshipService:

    @staticmethod
    def _canonical_user_ids(*, user_a: User, user_b: User) -> tuple[int, int]:
        if user_a.pk == user_b.pk:
            raise SelfFriendshipNotAllowed

        return tuple(
            sorted(
                (
                    user_a.pk,
                    user_b.pk,
                )
            )
        )

    @classmethod
    def _create_friendship(
        cls,
        *,
        user_a: User,
        user_b: User,
    ) -> Friendship:
        """
        Internal operation.

        Friendship creation is not a public V1 application command.
        It may only be called from a workflow that has already
        established a legal reason to create the friendship, which
        in V1 is friend-request acceptance.
        """

        user_1_id, user_2_id = cls._canonical_user_ids(
            user_a=user_a,
            user_b=user_b,
        )

        friendship, created = Friendship.objects.get_or_create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

        if not created:
            raise UsersAlreadyFriends

        return friendship

    @classmethod
    def remove_friendship(
        cls,
        *,
        current_user: User,
        friend_user_id: int,
    ) -> None:
        if current_user.pk == friend_user_id:
            raise FriendshipNotFound

        user_1_id, user_2_id = sorted(
            (
                current_user.pk,
                friend_user_id,
            )
        )

        with transaction.atomic():

            try:
                friendship = (
                    Friendship.objects
                    .select_for_update()
                    .get(
                        user_1_id=user_1_id,
                        user_2_id=user_2_id,
                    )
                )
            except Friendship.DoesNotExist as exc:
                raise FriendshipNotFound from exc

            user_a_id = friendship.user_1_id
            user_a_username = friendship.user_1.username
            user_b_id = friendship.user_2_id
            user_b_username = friendship.user_2.username

            friendship.delete()

            FriendshipRealtimePublisher.friendship_removed_after_commit(
                user_a_id=user_a_id,
                user_a_username=user_a_username,
                user_b_id=user_b_id,
                user_b_username=user_b_username,
            )
