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
