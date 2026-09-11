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

    GROUP_MEMBER_ADDED = "group.member_added"
    GROUP_MEMBER_REMOVED = "group.member_removed"
    GROUP_MEMBER_LEFT = "group.member_left"
    GROUP_RENAMED = "group.renamed"
    GROUP_DELETED = "group.deleted"

    TYPING_STARTED = "typing.started"
    TYPING_STOPPED = "typing.stopped"
    PRESENCE_UPDATED = "presence.updated"


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
