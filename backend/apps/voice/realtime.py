from collections.abc import Iterable
from uuid import UUID

from apps.realtime.events import RealtimeEventType
from apps.realtime.publisher import RealtimePublisher


class VoiceRealtimePublisher:
    """Publish committed voice-domain mutations to affected accounts."""

    @staticmethod
    def _session_id(value) -> str:
        return str(value)

    @staticmethod
    def _client_instance_id(value: UUID | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _timestamp(value) -> str:
        return value.isoformat().replace("+00:00", "Z")

    @classmethod
    def direct_call_ringing_after_commit(
        cls,
        *,
        session_id,
        caller_id: int,
        recipient_id: int,
        ring_expires_at,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[caller_id, recipient_id],
            event_type=RealtimeEventType.VOICE_DIRECT_CALL_RINGING,
            payload={
                "session_id": cls._session_id(session_id),
                "caller_id": caller_id,
                "recipient_id": recipient_id,
                "ring_expires_at": cls._timestamp(ring_expires_at),
            },
        )

    @classmethod
    def direct_call_accepted_after_commit(
        cls,
        *,
        session_id,
        caller_id: int,
        recipient_id: int,
        accepted_by_client_instance_id: UUID,
        activated_at,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[caller_id, recipient_id],
            event_type=RealtimeEventType.VOICE_DIRECT_CALL_ACCEPTED,
            payload={
                "session_id": cls._session_id(session_id),
                "caller_id": caller_id,
                "recipient_id": recipient_id,
                "accepted_by_client_instance_id": cls._client_instance_id(
                    accepted_by_client_instance_id
                ),
                "activated_at": cls._timestamp(activated_at),
            },
        )

    @classmethod
    def direct_call_ended_after_commit(
        cls,
        *,
        session_id,
        caller_id: int,
        recipient_id: int,
        end_reason: str,
        ended_at,
    ) -> None:
        event_type = {
            "REJECTED": RealtimeEventType.VOICE_DIRECT_CALL_REJECTED,
            "CANCELLED": RealtimeEventType.VOICE_DIRECT_CALL_CANCELLED,
            "MISSED": RealtimeEventType.VOICE_DIRECT_CALL_MISSED,
            "HANGUP": RealtimeEventType.VOICE_DIRECT_CALL_ENDED,
        }.get(
            end_reason,
            RealtimeEventType.VOICE_DIRECT_CALL_ENDED,
        )

        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[caller_id, recipient_id],
            event_type=event_type,
            payload={
                "session_id": cls._session_id(session_id),
                "caller_id": caller_id,
                "recipient_id": recipient_id,
                "end_reason": end_reason,
                "ended_at": cls._timestamp(ended_at),
            },
        )

    @classmethod
    def group_participant_joined_after_commit(
        cls,
        *,
        session_id,
        participation_id,
        group_id: int,
        user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_GROUP_PARTICIPANT_JOINED,
            payload={
                "session_id": cls._session_id(session_id),
                "participation_id": cls._session_id(participation_id),
                "group_id": group_id,
                "user_id": user_id,
            },
        )

    @classmethod
    def group_participant_left_after_commit(
        cls,
        *,
        session_id,
        participation_id,
        group_id: int,
        user_id: int,
        audience_user_ids: Iterable[int],
        session_ended: bool,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_GROUP_PARTICIPANT_LEFT,
            payload={
                "session_id": cls._session_id(session_id),
                "participation_id": cls._session_id(participation_id),
                "group_id": group_id,
                "user_id": user_id,
                "session_ended": session_ended,
            },
        )

    @classmethod
    def group_participant_revoked_after_commit(
        cls,
        *,
        session_id,
        participation_id,
        group_id: int,
        user_id: int,
        audience_user_ids: Iterable[int],
        session_ended: bool,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_GROUP_PARTICIPANT_REVOKED,
            payload={
                "session_id": cls._session_id(session_id),
                "participation_id": cls._session_id(participation_id),
                "group_id": group_id,
                "user_id": user_id,
                "session_ended": session_ended,
            },
        )

    @classmethod
    def group_session_ended_after_commit(
        cls,
        *,
        session_id,
        group_id: int,
        audience_user_ids: Iterable[int],
        end_reason: str,
        ended_at,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_GROUP_SESSION_ENDED,
            payload={
                "session_id": cls._session_id(session_id),
                "group_id": group_id,
                "end_reason": end_reason,
                "ended_at": cls._timestamp(ended_at),
            },
        )

    @classmethod
    def room_participant_joined_after_commit(
        cls,
        *,
        session_id,
        participation_id,
        room_id,
        user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_PARTICIPANT_JOINED,
            payload={
                "session_id": cls._session_id(session_id),
                "participation_id": cls._session_id(participation_id),
                "room_id": str(room_id),
                "user_id": user_id,
            },
        )

    @classmethod
    def room_participant_left_after_commit(
        cls,
        *,
        session_id,
        participation_id,
        room_id,
        user_id: int,
        audience_user_ids: Iterable[int],
        session_ended: bool,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_PARTICIPANT_LEFT,
            payload={
                "session_id": cls._session_id(session_id),
                "participation_id": cls._session_id(participation_id),
                "room_id": str(room_id),
                "user_id": user_id,
                "session_ended": session_ended,
            },
        )
