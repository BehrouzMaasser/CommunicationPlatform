from rest_framework import status
from rest_framework.response import Response

from apps.conversations.exceptions import (
    ConversationsError,
    DirectConversationTargetNotFound,
    FriendshipRequiredForDirectConversation,
    FriendshipRequiredForGroupInvitation,
    GroupInvitationAlreadyPending,
    GroupInvitationLinkNotFound,
    GroupInvitationNotFound,
    GroupInvitationRecipientRequired,
    GroupInvitationTargetNotFound,
    GroupMembershipNotFound,
    GroupNotFound,
    GroupOwnerCannotBeRemoved,
    GroupOwnerRequired,
    InvalidGroupInvitationLink,
    InvalidGroupName,
    SelfDirectConversationNotAllowed,
    UserAlreadyGroupMember,
)


_EXCEPTION_STATUS_MAP = {
    DirectConversationTargetNotFound:
        status.HTTP_404_NOT_FOUND,

    GroupNotFound:
        status.HTTP_404_NOT_FOUND,

    GroupMembershipNotFound:
        status.HTTP_404_NOT_FOUND,

    GroupInvitationTargetNotFound:
        status.HTTP_404_NOT_FOUND,

    GroupInvitationNotFound:
        status.HTTP_404_NOT_FOUND,

    GroupInvitationLinkNotFound:
        status.HTTP_404_NOT_FOUND,

    SelfDirectConversationNotAllowed:
        status.HTTP_400_BAD_REQUEST,

    InvalidGroupName:
        status.HTTP_400_BAD_REQUEST,

    InvalidGroupInvitationLink:
        status.HTTP_400_BAD_REQUEST,

    FriendshipRequiredForDirectConversation:
        status.HTTP_403_FORBIDDEN,

    FriendshipRequiredForGroupInvitation:
        status.HTTP_403_FORBIDDEN,

    GroupOwnerRequired:
        status.HTTP_403_FORBIDDEN,

    GroupInvitationRecipientRequired:
        status.HTTP_403_FORBIDDEN,

    UserAlreadyGroupMember:
        status.HTTP_409_CONFLICT,

    GroupInvitationAlreadyPending:
        status.HTTP_409_CONFLICT,

    GroupOwnerCannotBeRemoved:
        status.HTTP_409_CONFLICT,
}


def conversations_error_response(
    exc: ConversationsError,
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
