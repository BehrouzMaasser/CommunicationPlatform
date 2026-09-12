from collections.abc import Iterable
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from apps.realtime.events import (
    RealtimeEventType,
    build_realtime_event,
)
from apps.realtime.group_names import (
    ConversationType,
    conversation_group_name,
    user_group_name,
)


class RealtimePublisher:

    CHANNEL_EVENT_TYPE = "realtime.event"
    FORCE_UNSUBSCRIBE_EVENT_TYPE = "realtime.force_unsubscribe"

    @staticmethod
    def _channel_layer():
        channel_layer = get_channel_layer()

        if channel_layer is None:
            raise RuntimeError(
                "Realtime channel layer is not configured."
            )

        return channel_layer

    @classmethod
    def publish(
        cls,
        *,
        event_type: str | RealtimeEventType,
        payload: dict[str, Any],
        group_names: Iterable[str],
    ) -> dict[str, Any]:
        event = build_realtime_event(
            event_type=event_type,
            payload=payload,
        )

        channel_layer = cls._channel_layer()

        for group_name in set(group_names):
            async_to_sync(
                channel_layer.group_send
            )(
                group_name,
                {
                    "type": cls.CHANNEL_EVENT_TYPE,
                    "event": event,
                },
            )

        return event

    @classmethod
    def publish_after_commit(
        cls,
        *,
        event_type: str | RealtimeEventType,
        payload: dict[str, Any],
        group_names: Iterable[str],
    ) -> None:
        target_groups = tuple(
            set(group_names)
        )

        transaction.on_commit(
            lambda: cls.publish(
                event_type=event_type,
                payload=payload,
                group_names=target_groups,
            )
        )

    @classmethod
    def publish_to_user_after_commit(
        cls,
        *,
        user_id: int,
        event_type: str | RealtimeEventType,
        payload: dict[str, Any],
    ) -> None:
        cls.publish_after_commit(
            event_type=event_type,
            payload=payload,
            group_names=[
                user_group_name(user_id)
            ],
        )

    @classmethod
    def publish_to_users_after_commit(
        cls,
        *,
        user_ids: Iterable[int],
        event_type: str | RealtimeEventType,
        payload: dict[str, Any],
    ) -> None:
        cls.publish_after_commit(
            event_type=event_type,
            payload=payload,
            group_names=[
                user_group_name(user_id)
                for user_id in user_ids
            ],
        )

    @classmethod
    def publish_to_conversation_after_commit(
        cls,
        *,
        conversation_type: ConversationType,
        conversation_id: int,
        event_type: str | RealtimeEventType,
        payload: dict[str, Any],
    ) -> None:
        cls.publish_after_commit(
            event_type=event_type,
            payload=payload,
            group_names=[
                conversation_group_name(
                    conversation_type,
                    conversation_id,
                )
            ],
        )

    @classmethod
    def force_unsubscribe_user_from_conversation_after_commit(
        cls,
        *,
        user_id: int,
        conversation_type: ConversationType,
        conversation_id: int,
    ) -> None:
        """
        Server-side subscription revocation.

        This is intentionally an internal channel-layer command rather than a
        client event. Every socket belonging to user_id receives it through the
        personal user group, discards the forbidden conversation group, then
        tells the client that access was revoked.
        """
        user_group = user_group_name(user_id)
        target_group = conversation_group_name(
            conversation_type,
            conversation_id,
        )

        def force_unsubscribe() -> None:
            channel_layer = cls._channel_layer()

            async_to_sync(
                channel_layer.group_send
            )(
                user_group,
                {
                    "type": cls.FORCE_UNSUBSCRIBE_EVENT_TYPE,
                    "conversation_type": conversation_type,
                    "conversation_id": conversation_id,
                    "group_name": target_group,
                },
            )

        transaction.on_commit(
            force_unsubscribe
        )
