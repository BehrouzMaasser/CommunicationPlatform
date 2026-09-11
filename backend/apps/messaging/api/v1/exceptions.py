from rest_framework import status
from rest_framework.response import Response

from apps.messaging.exceptions import (
    InvalidMessageContent,
    FriendshipRequiredForDirectMessage,
    InvalidMessageContext,
    MessageContextNotFound,
    MessageNotFound,
    MessagingError,
    ReplyMessageNotFound,
)


_EXCEPTION_STATUS_MAP = {
    InvalidMessageContext:
        status.HTTP_400_BAD_REQUEST,

    InvalidMessageContent:
        status.HTTP_400_BAD_REQUEST,

    FriendshipRequiredForDirectMessage:
        status.HTTP_403_FORBIDDEN,

    MessageContextNotFound:
        status.HTTP_404_NOT_FOUND,

    ReplyMessageNotFound:
        status.HTTP_404_NOT_FOUND,

    MessageNotFound:
        status.HTTP_404_NOT_FOUND,
}


def messaging_error_response(
    exc: MessagingError,
) -> Response:
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
