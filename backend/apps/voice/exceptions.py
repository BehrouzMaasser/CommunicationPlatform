class VoiceError(Exception):
    """Base exception for voice-domain failures."""


class VoiceUnavailable(VoiceError):
    """Raised when voice infrastructure is disabled or not configured."""


class VoiceTargetUserNotFound(VoiceError):
    """Raised when a direct-call target does not exist."""


class SelfVoiceCallNotAllowed(VoiceError):
    """Raised when a user attempts to call themselves."""


class VoiceFriendshipRequired(VoiceError):
    """Raised when a direct call is started without a current friendship."""


class VoiceUserBusy(VoiceError):
    """Raised when a user already has an open voice participation."""


class VoiceSessionNotFound(VoiceError):
    """Raised when the requested voice session is not available to the user."""


class VoiceInvalidState(VoiceError):
    """Raised when an operation is invalid for the session lifecycle state."""


class VoiceCallPermissionDenied(VoiceError):
    """Raised when the caller/callee role does not permit the operation."""


class VoiceGroupNotFound(VoiceError):
    """Raised when a group requested for voice does not exist."""


class VoiceGroupMembershipRequired(VoiceError):
    """Raised when current group membership is required for voice access."""


class VoiceParticipationNotActive(VoiceError):
    """Raised when the user has no open participation in the session."""


class VoiceParticipationClaimed(VoiceError):
    """Raised when another client instance already owns the participation."""


class VoiceRoomNotFound(VoiceError):
    """Raised when a voice room does not exist or is not accessible."""


class VoiceRoomOwnerRequired(VoiceError):
    """Raised when an operation requires voice-room ownership."""


class VoiceRoomMembershipRequired(VoiceError):
    """Raised when current voice-room membership is required."""


class VoiceRoomOwnerCannotLeave(VoiceError):
    """Raised when the owner attempts to leave their own room."""


class VoiceRoomOwnerCannotBeRemoved(VoiceError):
    """Raised when an operation attempts to remove the room owner."""


class VoiceRoomNameRequired(VoiceError):
    """Raised when a voice-room name is empty."""


class VoiceRoomInvitationTargetNotFound(VoiceError):
    """Raised when the target user for a room invitation does not exist."""


class VoiceRoomInvitationNotFound(VoiceError):
    """Raised when a voice-room invitation does not exist."""


class VoiceRoomInvitationRecipientRequired(VoiceError):
    """Raised when only the invitation recipient may perform an action."""


class VoiceRoomInvitationAlreadyPending(VoiceError):
    """Raised when a pending invitation already exists."""


class VoiceRoomFriendshipRequired(VoiceError):
    """Raised when a direct room invitation targets a non-friend."""


class UserAlreadyVoiceRoomMember(VoiceError):
    """Raised when the target user already belongs to the voice room."""


class VoiceRoomInvitationLinkNotFound(VoiceError):
    """Raised when an invitation link record does not exist."""


class InvalidVoiceRoomInvitationLink(VoiceError):
    """Raised when an invitation link is invalid, expired, or revoked."""
