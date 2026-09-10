from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.friendships.exceptions import (
    FriendRequestAlreadyPending,
    FriendRequestNotFound,
    FriendRequestRecipientRequired,
    FriendRequestSenderRequired,
    SelfFriendRequestNotAllowed,
    TargetUserNotFound,
    UsersAlreadyFriends,
)
from apps.friendships.models import (
    FriendRequest,
    Friendship,
)
from apps.friendships.services.friendship import FriendshipService


User = get_user_model()


class FriendRequestService:

    @staticmethod
    def _pending_request_query(*, user_a: User, user_b: User) -> Q:

        return Q(sender=user_a, recipient=user_b) | Q(sender=user_b, recipient=user_a)

    @staticmethod
    def _friendship_exists(*, user_a: User, user_b: User) -> bool:

        user_1_id = min(user_a.pk, user_b.pk)
        user_2_id = max(user_a.pk, user_b.pk)

        return Friendship.objects.filter(user_1_id=user_1_id, user_2_id=user_2_id).exists()

    @staticmethod
    def _get_friend_request_for_update(*, friend_request_id: int) -> FriendRequest:

        try:
            return (
                FriendRequest.objects
                .select_for_update()
                .select_related(
                    "sender",
                    "recipient",
                )
                .get(pk=friend_request_id)
            )
        except FriendRequest.DoesNotExist as exc:
            raise FriendRequestNotFound from exc

    @classmethod
    def send_friend_request(cls, *, current_user: User, target_user_id: int) -> FriendRequest:

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist as exc:
            raise TargetUserNotFound from exc

        if current_user.pk == target_user.pk:
            raise SelfFriendRequestNotAllowed

        with transaction.atomic():
            if cls._friendship_exists(user_a=current_user, user_b=target_user):
                raise UsersAlreadyFriends

            pending_query = cls._pending_request_query(
                user_a=current_user,
                user_b=target_user,
            )

            if FriendRequest.objects.filter(pending_query).exists():
                raise FriendRequestAlreadyPending

            try:
                # Nested atomic block creates a savepoint so an
                # IntegrityError from the database constraint does
                # not break the surrounding transaction.
                with transaction.atomic():
                    friend_request = FriendRequest.objects.create(
                        sender=current_user,
                        recipient=target_user,
                    )

            except IntegrityError as exc:
                # Protect against concurrent attempts that passed
                # the application-level existence check together.
                if FriendRequest.objects.filter(pending_query).exists():
                    raise FriendRequestAlreadyPending from exc

                raise

            # Later:
            # transaction.on_commit(
            #     lambda: publish FriendRequestCreated(...)
            # )

        return friend_request

    @classmethod
    def accept_friend_request(cls, *, current_user: User, friend_request_id: int) -> Friendship:

        with transaction.atomic():
            friend_request = (
                cls._get_friend_request_for_update(
                    friend_request_id=friend_request_id,
                )
            )

            if friend_request.recipient_id != current_user.pk:
                raise FriendRequestRecipientRequired

            if friend_request.sender_id == friend_request.recipient_id:
                raise SelfFriendRequestNotAllowed

            if cls._friendship_exists(
                user_a=friend_request.sender,
                user_b=friend_request.recipient,
            ):
                raise UsersAlreadyFriends

            friendship = FriendshipService._create_friendship(
                user_a=friend_request.sender,
                user_b=friend_request.recipient,
            )

            friend_request.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish FriendRequestAccepted(...)
            # )
            #
            # transaction.on_commit(
            #     lambda: publish FriendshipCreated(...)
            # )

        return friendship

    @classmethod
    def reject_friend_request(cls, *, current_user: User, friend_request_id: int) -> None:

        with transaction.atomic():
            friend_request = cls._get_friend_request_for_update(
                friend_request_id=friend_request_id,
            )

            if friend_request.recipient_id != current_user.pk:
                raise FriendRequestRecipientRequired

            friend_request.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish FriendRequestRejected(...)
            # )

    @classmethod
    def cancel_pending_friend_request(cls, *, current_user: User, friend_request_id: int) -> None:

        with transaction.atomic():
            friend_request = cls._get_friend_request_for_update(
                friend_request_id=friend_request_id,
            )

            if friend_request.sender_id != current_user.pk:
                raise FriendRequestSenderRequired

            friend_request.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish FriendRequestCancelled(...)
            # )
