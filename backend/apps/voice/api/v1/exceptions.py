from rest_framework import status
from rest_framework.response import Response

from apps.voice.exceptions import (
    VoiceRoomInvitationLinkNotFound,
    InvalidVoiceRoomInvitationLink,
    InvalidVoiceRoomAvatar,
    SelfVoiceCallNotAllowed,
    VoiceCallPermissionDenied,
    VoiceError,
    VoiceFriendshipRequired,
    VoiceGroupMembershipRequired,
    VoiceGroupNotFound,
    VoiceInvalidState,
    VoiceParticipationClaimed,
    VoiceParticipationNotActive,
    UserAlreadyVoiceRoomMember,
    VoiceRoomFriendshipRequired,
    VoiceRoomInvitationAlreadyPending,
    VoiceRoomInvitationNotFound,
    VoiceRoomInvitationRecipientRequired,
    VoiceRoomInvitationTargetNotFound,
    VoiceRoomMembershipRequired,
    VoiceRoomNameRequired,
    VoiceRoomNotFound,
    VoiceRoomOwnerCannotBeRemoved,
    VoiceRoomOwnerCannotLeave,
    VoiceRoomOwnerRequired,
    VoiceSessionNotFound,
    VoiceTargetUserNotFound,
    VoiceUnavailable,
    VoiceUserBusy,
)


_EXCEPTION_MAP = {
    VoiceUnavailable: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "VOICE_UNAVAILABLE",
        "Voice communication is currently unavailable.",
    ),
    VoiceTargetUserNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_TARGET_NOT_FOUND",
        "The requested user was not found.",
    ),
    SelfVoiceCallNotAllowed: (
        status.HTTP_400_BAD_REQUEST,
        "SELF_VOICE_CALL_NOT_ALLOWED",
        "You cannot start a voice call with yourself.",
    ),
    VoiceFriendshipRequired: (
        status.HTTP_403_FORBIDDEN,
        "VOICE_FRIENDSHIP_REQUIRED",
        "A current friendship is required to start this call.",
    ),
    VoiceUserBusy: (
        status.HTTP_409_CONFLICT,
        "VOICE_USER_BUSY",
        "One of the users is already reserved by another voice session.",
    ),
    VoiceSessionNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_SESSION_NOT_FOUND",
        "The requested voice session was not found.",
    ),
    VoiceInvalidState: (
        status.HTTP_409_CONFLICT,
        "VOICE_INVALID_STATE",
        "The requested operation is not valid for the current voice state.",
    ),
    VoiceCallPermissionDenied: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_SESSION_NOT_FOUND",
        "The requested voice session was not found.",
    ),
    VoiceGroupNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_GROUP_NOT_FOUND",
        "The requested group was not found.",
    ),
    VoiceGroupMembershipRequired: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_GROUP_NOT_FOUND",
        "The requested group was not found.",
    ),
    VoiceParticipationNotActive: (
        status.HTTP_409_CONFLICT,
        "VOICE_PARTICIPATION_NOT_ACTIVE",
        "There is no active voice participation for this operation.",
    ),
    VoiceParticipationClaimed: (
        status.HTTP_409_CONFLICT,
        "VOICE_PARTICIPATION_CLAIMED",
        "This voice participation is owned by another client instance.",
    ),
    VoiceRoomNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_NOT_FOUND",
        "The requested voice room was not found.",
    ),
    VoiceRoomMembershipRequired: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_MEMBERSHIP_NOT_FOUND",
        "The requested voice-room membership was not found.",
    ),
    VoiceRoomOwnerRequired: (
        status.HTTP_403_FORBIDDEN,
        "VOICE_ROOM_OWNER_REQUIRED",
        "Only the voice-room owner may perform this action.",
    ),
    VoiceRoomOwnerCannotLeave: (
        status.HTTP_409_CONFLICT,
        "VOICE_ROOM_OWNER_CANNOT_LEAVE",
        "The voice-room owner cannot leave their own room.",
    ),
    VoiceRoomOwnerCannotBeRemoved: (
        status.HTTP_409_CONFLICT,
        "VOICE_ROOM_OWNER_CANNOT_BE_REMOVED",
        "The voice-room owner cannot be removed.",
    ),
    VoiceRoomNameRequired: (
        status.HTTP_400_BAD_REQUEST,
        "VOICE_ROOM_NAME_REQUIRED",
        "A voice-room name is required.",
    ),
    InvalidVoiceRoomAvatar: (
        status.HTTP_400_BAD_REQUEST,
        "INVALID_VOICE_ROOM_AVATAR",
        "The voice-room avatar is invalid.",
    ),
    VoiceRoomInvitationTargetNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_INVITATION_TARGET_NOT_FOUND",
        "The requested invitation target was not found.",
    ),
    VoiceRoomInvitationNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_INVITATION_NOT_FOUND",
        "The requested voice-room invitation was not found.",
    ),
    VoiceRoomInvitationRecipientRequired: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_INVITATION_NOT_FOUND",
        "The requested voice-room invitation was not found.",
    ),
    VoiceRoomInvitationAlreadyPending: (
        status.HTTP_409_CONFLICT,
        "VOICE_ROOM_INVITATION_ALREADY_PENDING",
        "A pending invitation already exists for this user.",
    ),
    VoiceRoomFriendshipRequired: (
        status.HTTP_403_FORBIDDEN,
        "VOICE_ROOM_FRIENDSHIP_REQUIRED",
        "A current friendship is required to invite this user.",
    ),
    UserAlreadyVoiceRoomMember: (
        status.HTTP_409_CONFLICT,
        "USER_ALREADY_VOICE_ROOM_MEMBER",
        "The user is already a member of this voice room.",
    ),
    VoiceRoomInvitationLinkNotFound: (
        status.HTTP_404_NOT_FOUND,
        "VOICE_ROOM_INVITATION_LINK_NOT_FOUND",
        "The requested voice-room invitation link was not found.",
    ),
    InvalidVoiceRoomInvitationLink: (
        status.HTTP_400_BAD_REQUEST,
        "INVALID_VOICE_ROOM_INVITATION_LINK",
        "The voice-room invitation link is invalid, expired, or revoked.",
    ),
}


def voice_error_response(exc: VoiceError) -> Response:
    status_code, code, default_detail = _EXCEPTION_MAP.get(
        type(exc),
        (
            status.HTTP_400_BAD_REQUEST,
            "VOICE_ERROR",
            "The voice operation could not be completed.",
        ),
    )

    detail = str(exc).strip() or default_detail

    return Response(
        {
            "code": code,
            "detail": detail,
        },
        status=status_code,
    )
