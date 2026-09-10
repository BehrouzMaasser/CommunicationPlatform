from rest_framework import status
from rest_framework.response import Response

from apps.friendships.exceptions import (
    FriendRequestAlreadyPending,
    FriendRequestNotFound,
    FriendRequestRecipientRequired,
    FriendRequestSenderRequired,
    FriendshipNotFound,
    SelfFriendRequestNotAllowed,
    TargetUserNotFound,
    UsersAlreadyFriends,
)


_EXCEPTION_STATUS_MAP = {
    TargetUserNotFound: status.HTTP_404_NOT_FOUND,
    FriendRequestNotFound: status.HTTP_404_NOT_FOUND,
    FriendshipNotFound: status.HTTP_404_NOT_FOUND,

    SelfFriendRequestNotAllowed: status.HTTP_400_BAD_REQUEST,

    FriendRequestRecipientRequired: status.HTTP_403_FORBIDDEN,
    FriendRequestSenderRequired: status.HTTP_403_FORBIDDEN,

    FriendRequestAlreadyPending: status.HTTP_409_CONFLICT,
    UsersAlreadyFriends: status.HTTP_409_CONFLICT,
}


def friendships_error_response(exc):
    status_code = _EXCEPTION_STATUS_MAP.get(
        type(exc),
        status.HTTP_400_BAD_REQUEST,
    )

    return Response(
        {
            "detail": exc.message,
        },
        status=status_code,
    )
