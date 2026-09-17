from collections.abc import Iterable

from apps.realtime.events import RealtimeEventType
from apps.realtime.publisher import RealtimePublisher


class VoiceRoomRealtimePublisher:
    """Publish committed persistent VoiceRoom mutations."""

    @staticmethod
    def _id(value) -> str:
        return str(value)

    @staticmethod
    def _timestamp(value) -> str:
        return (
            value.isoformat()
            .replace("+00:00", "Z")
        )

    @classmethod
    def room_created_after_commit(
        cls,
        *,
        room_id,
        room_name: str,
        owner_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[owner_id],
            event_type=RealtimeEventType.VOICE_ROOM_CREATED,
            payload={
                "room_id": cls._id(room_id),
                "room_name": room_name,
                "owner_id": owner_id,
            },
        )

    @classmethod
    def room_renamed_after_commit(
        cls,
        *,
        room_id,
        room_name: str,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_RENAMED,
            payload={
                "room_id": cls._id(room_id),
                "room_name": room_name,
            },
        )

    @classmethod
    def room_avatar_updated_after_commit(
        cls,
        *,
        room_id,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_AVATAR_UPDATED
            ),
            payload={
                "room_id": cls._id(room_id),
            },
        )

    @classmethod
    def room_deleted_after_commit(
        cls,
        *,
        room_id,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_DELETED,
            payload={
                "room_id": cls._id(room_id),
            },
        )

    @classmethod
    def member_added_after_commit(
        cls,
        *,
        room_id,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_MEMBER_ADDED,
            payload={
                "room_id": cls._id(room_id),
                "member_user_id": member_user_id,
            },
        )

    @classmethod
    def member_left_after_commit(
        cls,
        *,
        room_id,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_MEMBER_LEFT,
            payload={
                "room_id": cls._id(room_id),
                "member_user_id": member_user_id,
            },
        )

    @classmethod
    def member_removed_after_commit(
        cls,
        *,
        room_id,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=audience_user_ids,
            event_type=RealtimeEventType.VOICE_ROOM_MEMBER_REMOVED,
            payload={
                "room_id": cls._id(room_id),
                "member_user_id": member_user_id,
            },
        )

    @classmethod
    def invitation_created_after_commit(
        cls,
        *,
        invitation_id,
        room_id,
        room_name: str,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITATION_CREATED
            ),
            payload={
                "invitation_id": cls._id(
                    invitation_id
                ),
                "room_id": cls._id(room_id),
                "room_name": room_name,
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
        )

    @classmethod
    def invitation_accepted_after_commit(
        cls,
        *,
        invitation_id,
        room_id,
        room_name: str,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITATION_ACCEPTED
            ),
            payload={
                "invitation_id": cls._id(
                    invitation_id
                ),
                "room_id": cls._id(room_id),
                "room_name": room_name,
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
        )

    @classmethod
    def invitation_rejected_after_commit(
        cls,
        *,
        invitation_id,
        room_id,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITATION_REJECTED
            ),
            payload={
                "invitation_id": cls._id(
                    invitation_id
                ),
                "room_id": cls._id(room_id),
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
        )

    @classmethod
    def invitation_cancelled_after_commit(
        cls,
        *,
        invitation_id,
        room_id,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITATION_CANCELLED
            ),
            payload={
                "invitation_id": cls._id(
                    invitation_id
                ),
                "room_id": cls._id(room_id),
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
        )

    @classmethod
    def invite_link_created_after_commit(
        cls,
        *,
        link_id,
        room_id,
        owner_id: int,
        expires_at,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[owner_id],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITE_LINK_CREATED
            ),
            payload={
                "link_id": cls._id(link_id),
                "room_id": cls._id(room_id),
                "expires_at": cls._timestamp(
                    expires_at
                ),
            },
        )

    @classmethod
    def invite_link_revoked_after_commit(
        cls,
        *,
        link_id,
        room_id,
        owner_id: int,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[owner_id],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITE_LINK_REVOKED
            ),
            payload={
                "link_id": cls._id(link_id),
                "room_id": cls._id(room_id),
            },
        )
