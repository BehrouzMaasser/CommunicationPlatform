from apps.accounts.avatar_urls import build_avatar_url
from apps.realtime.events import RealtimeEventType
from apps.realtime.publisher import RealtimePublisher


class FriendshipRealtimePublisher:
    """
    Realtime adapter for committed friendship-domain mutations.

    Only primitive user data is passed into this adapter. That is deliberate:
    accept/reject/cancel/remove operations delete rows, so event publication
    must not depend on lazy access to those deleted relationship rows.
    """

    @staticmethod
    def _user_payload(
        *,
        user_id: int,
        username: str,
        avatar_name: str | None = None,
    ) -> dict:
        return {
            "id": user_id,
            "username": username,
            "avatar_url": build_avatar_url(
                user_id=user_id,
                avatar_name=avatar_name,
            ),
        }

    @classmethod
    def friend_request_created_after_commit(
        cls,
        *,
        request_id: int,
        sender_id: int,
        sender_username: str,
        recipient_id: int,
        recipient_username: str,
        sender_avatar_name: str | None = None,
        recipient_avatar_name: str | None = None,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                sender_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .FRIEND_REQUEST_CREATED
            ),
            payload={
                "request_id": request_id,
                "sender": cls._user_payload(
                    user_id=sender_id,
                    username=sender_username,
                    avatar_name=sender_avatar_name,
                ),
                "recipient": cls._user_payload(
                    user_id=recipient_id,
                    username=recipient_username,
                    avatar_name=recipient_avatar_name,
                ),
            },
        )

    @classmethod
    def friend_request_accepted_after_commit(
        cls,
        *,
        request_id: int,
        sender_id: int,
        sender_username: str,
        recipient_id: int,
        recipient_username: str,
        friendship_id: int,
        sender_avatar_name: str | None = None,
        recipient_avatar_name: str | None = None,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                sender_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .FRIEND_REQUEST_ACCEPTED
            ),
            payload={
                "request_id": request_id,
                "friendship_id": friendship_id,
                "sender": cls._user_payload(
                    user_id=sender_id,
                    username=sender_username,
                    avatar_name=sender_avatar_name,
                ),
                "recipient": cls._user_payload(
                    user_id=recipient_id,
                    username=recipient_username,
                    avatar_name=recipient_avatar_name,
                ),
            },
        )

    @classmethod
    def friend_request_rejected_after_commit(
        cls,
        *,
        request_id: int,
        sender_id: int,
        sender_username: str,
        recipient_id: int,
        recipient_username: str,
        sender_avatar_name: str | None = None,
        recipient_avatar_name: str | None = None,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                sender_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .FRIEND_REQUEST_REJECTED
            ),
            payload={
                "request_id": request_id,
                "sender": cls._user_payload(
                    user_id=sender_id,
                    username=sender_username,
                    avatar_name=sender_avatar_name,
                ),
                "recipient": cls._user_payload(
                    user_id=recipient_id,
                    username=recipient_username,
                    avatar_name=recipient_avatar_name,
                ),
            },
        )

    @classmethod
    def friend_request_cancelled_after_commit(
        cls,
        *,
        request_id: int,
        sender_id: int,
        sender_username: str,
        recipient_id: int,
        recipient_username: str,
        sender_avatar_name: str | None = None,
        recipient_avatar_name: str | None = None,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                sender_id,
                recipient_id,
            ],
            event_type=(
                RealtimeEventType
                .FRIEND_REQUEST_CANCELLED
            ),
            payload={
                "request_id": request_id,
                "sender": cls._user_payload(
                    user_id=sender_id,
                    username=sender_username,
                    avatar_name=sender_avatar_name,
                ),
                "recipient": cls._user_payload(
                    user_id=recipient_id,
                    username=recipient_username,
                    avatar_name=recipient_avatar_name,
                ),
            },
        )

    @classmethod
    def friendship_removed_after_commit(
        cls,
        *,
        user_a_id: int,
        user_a_username: str,
        user_b_id: int,
        user_b_username: str,
        user_a_avatar_name: str | None = None,
        user_b_avatar_name: str | None = None,
    ) -> None:
        RealtimePublisher.publish_to_users_after_commit(
            user_ids=[
                user_a_id,
                user_b_id,
            ],
            event_type=(
                RealtimeEventType
                .FRIENDSHIP_REMOVED
            ),
            payload={
                "user_a": cls._user_payload(
                    user_id=user_a_id,
                    username=user_a_username,
                    avatar_name=user_a_avatar_name,
                ),
                "user_b": cls._user_payload(
                    user_id=user_b_id,
                    username=user_b_username,
                    avatar_name=user_b_avatar_name,
                ),
            },
        )
