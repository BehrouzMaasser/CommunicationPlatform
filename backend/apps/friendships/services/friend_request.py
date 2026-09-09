from django.contrib.auth import authenticate, get_user_model, logout
from django.core.exceptions import ValidationError
from django.db.models import Q

from backend.apps.friendships.models import (
    FriendRequest,
    Friendship,
)

User = get_user_model()


class FriendRequestService:

    @staticmethod
    def send_friend_request(*, current_user: User, target_user_id: int) -> FriendRequest:

        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            raise InvalidProcess(code=TARGET_USER_NOT_FOUND)

        if target_user.pk == current_user.pk:
            raise BusinessRuleViolation(code=CANNOT_REQUEST_FRIENSSHIP_TO_SELF)

        if FriendshipService.are_friends(user_a=current_user, user_b=target_user):
            raise BusinessRuleViolation(code=USERS_ARE_ALREADY_FRIENDS)

        if FriendRequest.objects.filter(recipient=current_user, sender=target_user).exists():
            raise BusinessRuleViolation(code=RECIPIENT_ALREADY_SENT_A_FRIEND_REQUEST)

        friend_request = FriendRequest(
            sender=current_user,
            recipient=target_user
        )

        try:
            friend_request.full_clean()
            friend_request.save()
        except ValidationError as e:
            if e.code == "request_is_sent_and_is_pending":
                raise BusinessRuleViolation(code=EXISTING_FRIEND_REQUEST_IS_ALREADY_PENDING)

        # Probably notify the recipient using something

        return friend_request


    @staticmethod
    def cancel_pending_friend_request(*, current_user: User, friend_request_id: int) -> None:

        # Probably notify the recipient using something (remove the friend request from other side)

        friend_request = FriendRequestService.get_friend_request(friend_request_id=friend_request_id)

        if friend_request.sender.pk != current_user.pk:
            raise InvalidProcess(code=ONLY_FRIEND_REQUEST_SENDER_CAN_CANCEL)

        if not FriendRequestService.remove_friend_request_if_users_are_friends(current_user=current_user, friend_request=friend_request):
            friend_request.delete()


    @staticmethod
    def accept_friend_request(*, current_user: User, friend_request_id: int) -> None:

        # Probably notify the sender using something (remove the friend request from other side)

        friend_request = FriendRequestService.get_friend_request(friend_request_id=friend_request_id)

        if friend_request.recipient.pk != current_user.pk:
            raise InvalidProcess(code=ONLY_FRIEND_REQUEST_RECIPIENT_CAN_ACCEPT)

        if not FriendRequestService.remove_friend_request_if_users_are_friends(current_user=current_user, friend_request=friend_request):
            friend_request.delete()

        # Probably start the friendship
        FriendshipService.create(current_a=friend_request.recipient, user_b=friend_request.sender)

    @staticmethod
    def reject_friend_request(*, current_user: User, friend_request_id: int) -> None:

        # Probably notify the sender using something (remove the friend request from other side)

        friend_request = FriendRequestService.get_friend_request(friend_request_id=friend_request_id)

        if friend_request.recipient.pk != current_user.pk:
            raise InvalidProcess(code=ONLY_FRIEND_REQUEST_RECIPIENT_CAN_REJECT)

        if not FriendRequestService.remove_friend_request_if_users_are_friends(current_user=current_user, friend_request=friend_request):
            friend_request.delete()

    @staticmethod
    def get_friend_request(*, friend_request_id: int) -> FriendRequest:

        try:
            friend_request = FriendRequest.objects.get(pk=friend_request_id)
        except FriendRequest.DoesNotExist:
            raise InvalidProcess(code=TARGET_FRIEND_REQUEST_NOT_FOUND)

        return friend_request

    @staticmethod
    def remove_friend_request_if_users_are_friends(current_user: User, friend_request: FriendRequest, raise_error: bool = True) -> bool:

        if FriendshipService.are_friends(user_a=current_user, user_b=friend_request.recipient):
            friend_request.delete()
            if raise_error:
                raise InvalidProcess(code=USERS_ARE_ALREADY_FRIENDS)
            return True

        return False