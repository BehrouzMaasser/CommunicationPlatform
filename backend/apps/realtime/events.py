from enum import Enum
from typing import Any
from uuid import uuid4

from django.utils import timezone


class RealtimeEventType(str, Enum):
    CONNECTION_CONNECTED = "connection.connected"

    CONVERSATION_SUBSCRIBED = "conversation.subscribed"
    CONVERSATION_UNSUBSCRIBED = "conversation.unsubscribed"

    MESSAGE_CREATED = "message.created"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_READ = "message.read"

    FRIEND_REQUEST_CREATED = "friend_request.created"
    FRIEND_REQUEST_ACCEPTED = "friend_request.accepted"
    FRIEND_REQUEST_REJECTED = "friend_request.rejected"
    FRIEND_REQUEST_CANCELLED = "friend_request.cancelled"
    FRIENDSHIP_REMOVED = "friendship.removed"

    GROUP_INVITATION_CREATED = "group_invitation.created"
    GROUP_INVITATION_ACCEPTED = "group_invitation.accepted"
    GROUP_INVITATION_REJECTED = "group_invitation.rejected"
    GROUP_INVITATION_CANCELLED = "group_invitation.cancelled"

    GROUP_MEMBER_ADDED = "group.member_added"
    GROUP_MEMBER_REMOVED = "group.member_removed"
    GROUP_MEMBER_LEFT = "group.member_left"
    GROUP_RENAMED = "group.renamed"
    GROUP_AVATAR_UPDATED = "group.avatar_updated"
    GROUP_DELETED = "group.deleted"

    TYPING_STARTED = "typing.started"
    TYPING_STOPPED = "typing.stopped"
    PRESENCE_UPDATED = "presence.updated"

    VOICE_DIRECT_CALL_RINGING = "voice.direct_call.ringing"
    VOICE_DIRECT_CALL_ACCEPTED = "voice.direct_call.accepted"
    VOICE_DIRECT_CALL_REJECTED = "voice.direct_call.rejected"
    VOICE_DIRECT_CALL_CANCELLED = "voice.direct_call.cancelled"
    VOICE_DIRECT_CALL_MISSED = "voice.direct_call.missed"
    VOICE_DIRECT_CALL_ENDED = "voice.direct_call.ended"

    VOICE_GROUP_PARTICIPANT_JOINED = "voice.group.participant_joined"
    VOICE_GROUP_PARTICIPANT_LEFT = "voice.group.participant_left"
    VOICE_GROUP_PARTICIPANT_REVOKED = "voice.group.participant_revoked"
    VOICE_GROUP_SESSION_ENDED = "voice.group.session_ended"

    VOICE_ROOM_PARTICIPANT_JOINED = "voice.room.participant_joined"
    VOICE_ROOM_PARTICIPANT_LEFT = "voice.room.participant_left"
    VOICE_ROOM_PARTICIPANT_REVOKED = "voice.room.participant_revoked"
    VOICE_ROOM_SESSION_ENDED = "voice.room.session_ended"

    VOICE_ROOM_CREATED = "voice_room.created"
    VOICE_ROOM_RENAMED = "voice_room.renamed"
    VOICE_ROOM_AVATAR_UPDATED = "voice_room.avatar_updated"
    VOICE_ROOM_DELETED = "voice_room.deleted"

    VOICE_ROOM_MEMBER_ADDED = "voice_room.member_added"
    VOICE_ROOM_MEMBER_LEFT = "voice_room.member_left"
    VOICE_ROOM_MEMBER_REMOVED = "voice_room.member_removed"

    VOICE_ROOM_INVITATION_CREATED = "voice_room_invitation.created"
    VOICE_ROOM_INVITATION_ACCEPTED = "voice_room_invitation.accepted"
    VOICE_ROOM_INVITATION_REJECTED = "voice_room_invitation.rejected"
    VOICE_ROOM_INVITATION_CANCELLED = "voice_room_invitation.cancelled"

    VOICE_ROOM_INVITE_LINK_CREATED = "voice_room.invite_link_created"
    VOICE_ROOM_INVITE_LINK_REVOKED = "voice_room.invite_link_revoked"


def build_realtime_event(
    *,
    event_type: str | RealtimeEventType,
    payload: dict[str, Any],
    request_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "type": str(event_type.value)
        if isinstance(
            event_type,
            RealtimeEventType,
        )
        else event_type,
        "event_id": str(uuid4()),
        "timestamp": (
            timezone.now()
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "payload": payload,
    }

    if request_id is not None:
        event["request_id"] = request_id

    return event


def build_realtime_error(
    *,
    code: str,
    detail: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    event = build_realtime_event(
        event_type="error",
        payload={
            "code": code,
            "detail": detail,
        },
        request_id=request_id,
    )

    return event
