from datetime import datetime, timezone
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)

from apps.realtime.events import (
    RealtimeEventType,
    build_realtime_error,
    build_realtime_event,
)
from apps.realtime.group_names import (
    conversation_group_name,
    user_group_name,
)
from apps.realtime.subscriptions import (
    RealtimeSubscriptionSelector,
)
from apps.messaging.exceptions import MessagingError
from apps.messaging.services.receipt import MessageReceiptService
from apps.realtime.ephemeral import RealtimeEphemeralSelector
from apps.realtime.presence import PresenceStore


class RealtimeConsumer(
    AsyncJsonWebsocketConsumer
):

    CLOSE_NOT_AUTHENTICATED = 4401

    async def connect(self):
        user = self.scope.get("user")

        if (
            user is None
            or not user.is_authenticated
        ):
            await self.close(
                code=self.CLOSE_NOT_AUTHENTICATED,
            )
            return

        self.user = user
        self.user_group = user_group_name(
            user.pk,
        )
        self.subscribed_groups: set[str] = (
            set()
        )

        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name,
        )

        await self.accept()

        await self.send_json(
            build_realtime_event(
                event_type=(
                    RealtimeEventType
                    .CONNECTION_CONNECTED
                ),
                payload={
                    "user_id": user.pk,
                },
            )
        )

        expires_at = (
            await PresenceStore.touch(
                user_id=user.pk,
                connection_id=(
                    self.channel_name
                ),
            )
        )

        await self._broadcast_presence(
            expires_at=expires_at,
        )

        await self._send_presence_snapshot()

    async def disconnect(
        self,
        close_code: int,
    ):
        user_group = getattr(
            self,
            "user_group",
            None,
        )

        if user_group is not None:
            await (
                self.channel_layer
                .group_discard(
                    user_group,
                    self.channel_name,
                )
            )

        for group_name in getattr(
            self,
            "subscribed_groups",
            set(),
        ):
            await (
                self.channel_layer
                .group_discard(
                    group_name,
                    self.channel_name,
                )
            )

        user = getattr(
            self,
            "user",
            None,
        )

        if user is not None:
            remaining_until = (
                await PresenceStore.remove(
                    user_id=user.pk,
                    connection_id=(
                        self.channel_name
                    ),
                )
            )

            await self._broadcast_presence(
                expires_at=remaining_until,
            )

    async def receive_json(
        self,
        content: Any,
        **kwargs,
    ):
        if not isinstance(content, dict):
            await self._send_error(
                request_id=None,
                code="INVALID_COMMAND",
                detail=(
                    "Realtime command must "
                    "be an object."
                ),
            )
            return

        command_type = content.get("type")
        request_id = content.get(
            "request_id"
        )
        payload = content.get(
            "payload",
            {},
        )

        if not isinstance(payload, dict):
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "Command payload must "
                    "be an object."
                ),
            )
            return

        if (
            command_type
            == "conversation.subscribe"
        ):
            await (
                self
                ._handle_conversation_subscribe(
                    request_id=request_id,
                    payload=payload,
                )
            )
            return

        if (
            command_type
            == "conversation.unsubscribe"
        ):
            await (
                self
                ._handle_conversation_unsubscribe(
                    request_id=request_id,
                    payload=payload,
                )
            )
            return

        if (
            command_type
            == "message.delivered"
        ):
            await self._handle_message_delivered(
                request_id=request_id,
                payload=payload,
            )
            return

        if (
            command_type
            == "message.read"
        ):
            await self._handle_message_read(
                request_id=request_id,
                payload=payload,
            )
            return

        if (
            command_type
            == "presence.heartbeat"
        ):
            await (
                self
                ._handle_presence_heartbeat()
            )
            return

        if command_type in {
            "typing.start",
            "typing.stop",
        }:
            await self._handle_typing(
                command_type=command_type,
                request_id=request_id,
                payload=payload,
            )
            return

        await self._send_error(
            request_id=request_id,
            code="UNKNOWN_COMMAND",
            detail=(
                "This realtime command "
                "is not supported."
            ),
        )

    @staticmethod
    def _parse_message_id(
        payload: dict[str, Any],
    ) -> int | None:
        message_id = payload.get(
            "message_id"
        )

        if (
            isinstance(message_id, bool)
            or not isinstance(
                message_id,
                int,
            )
            or message_id <= 0
        ):
            return None

        return message_id

    @database_sync_to_async
    def _mark_message_delivered(
        self,
        *,
        message_id: int,
    ) -> None:
        (
            MessageReceiptService
            .mark_delivered(
                current_user=self.user,
                message_id=message_id,
            )
        )

    @database_sync_to_async
    def _mark_message_read(
        self,
        *,
        message_id: int,
    ) -> None:
        (
            MessageReceiptService
            .mark_read_through(
                current_user=self.user,
                message_id=message_id,
            )
        )

    async def _handle_message_delivered(
        self,
        *,
        request_id: str | None,
        payload: dict[str, Any],
    ):
        message_id = (
            self._parse_message_id(
                payload
            )
        )

        if message_id is None:
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "A valid message_id "
                    "is required."
                ),
            )
            return

        try:
            await self._mark_message_delivered(
                message_id=message_id,
            )
        except MessagingError:
            await self._send_error(
                request_id=request_id,
                code="NOT_AUTHORIZED",
                detail=(
                    "You cannot acknowledge "
                    "this message."
                ),
            )

    async def _handle_message_read(
        self,
        *,
        request_id: str | None,
        payload: dict[str, Any],
    ):
        message_id = (
            self._parse_message_id(
                payload
            )
        )

        if message_id is None:
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "A valid message_id "
                    "is required."
                ),
            )
            return

        try:
            await self._mark_message_read(
                message_id=message_id,
            )
        except MessagingError:
            await self._send_error(
                request_id=request_id,
                code="NOT_AUTHORIZED",
                detail=(
                    "You cannot mark "
                    "this message read."
                ),
            )

    @database_sync_to_async
    def _friend_user_ids(
        self,
    ) -> list[int]:
        return (
            RealtimeEphemeralSelector
            .friend_user_ids(
                user_id=self.user.pk,
            )
        )

    @database_sync_to_async
    def _can_publish_typing(
        self,
        *,
        conversation_type: str,
        conversation_id: int,
    ) -> bool:
        return (
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.user.pk,
                conversation_type=(
                    conversation_type
                ),
                conversation_id=(
                    conversation_id
                ),
            )
        )

    @staticmethod
    def _expires_at_iso(
        expires_at: float | None,
    ) -> str | None:
        if expires_at is None:
            return None

        return (
            datetime.fromtimestamp(
                expires_at,
                tz=timezone.utc,
            )
            .isoformat()
            .replace("+00:00", "Z")
        )

    async def _broadcast_presence(
        self,
        *,
        expires_at: float | None,
    ) -> None:
        friend_ids = (
            await self._friend_user_ids()
        )

        if not friend_ids:
            return

        event = build_realtime_event(
            event_type=(
                RealtimeEventType
                .PRESENCE_UPDATED
            ),
            payload={
                "user_id":
                    self.user.pk,
                "online":
                    expires_at
                    is not None,
                "expires_at":
                    self._expires_at_iso(
                        expires_at
                    ),
            },
        )

        for friend_id in friend_ids:
            await (
                self.channel_layer
                .group_send(
                    user_group_name(
                        friend_id
                    ),
                    {
                        "type":
                            "realtime.event",
                        "event":
                            event,
                    },
                )
            )

    async def _send_presence_snapshot(
        self,
    ) -> None:
        friend_ids = (
            await self._friend_user_ids()
        )

        for friend_id in friend_ids:
            expires_at = (
                await PresenceStore
                .online_until(
                    user_id=friend_id,
                )
            )

            await self.send_json(
                build_realtime_event(
                    event_type=(
                        RealtimeEventType
                        .PRESENCE_UPDATED
                    ),
                    payload={
                        "user_id":
                            friend_id,
                        "online":
                            expires_at
                            is not None,
                        "expires_at":
                            self._expires_at_iso(
                                expires_at
                            ),
                    },
                )
            )

    async def _handle_presence_heartbeat(
        self,
    ) -> None:
        expires_at = (
            await PresenceStore.touch(
                user_id=self.user.pk,
                connection_id=(
                    self.channel_name
                ),
            )
        )

        await self._broadcast_presence(
            expires_at=expires_at,
        )

    async def _handle_typing(
        self,
        *,
        command_type: str,
        request_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        parsed = self._parse_conversation(
            payload
        )

        if parsed is None:
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "A valid conversation_type "
                    "and conversation_id are required."
                ),
            )
            return

        (
            conversation_type,
            conversation_id,
        ) = parsed

        group_name = (
            conversation_group_name(
                conversation_type,
                conversation_id,
            )
        )

        # Typing is only meaningful from a socket that currently has this
        # conversation open/subscribed.
        if (
            group_name
            not in self.subscribed_groups
        ):
            await self._send_error(
                request_id=request_id,
                code="NOT_AUTHORIZED",
                detail=(
                    "You cannot publish typing "
                    "state for this conversation."
                ),
            )
            return

        can_publish = (
            await self._can_publish_typing(
                conversation_type=(
                    conversation_type
                ),
                conversation_id=(
                    conversation_id
                ),
            )
        )

        if not can_publish:
            await self._send_error(
                request_id=request_id,
                code="NOT_AUTHORIZED",
                detail=(
                    "You cannot publish typing "
                    "state for this conversation."
                ),
            )
            return

        event_type = (
            RealtimeEventType
            .TYPING_STARTED
            if command_type
            == "typing.start"
            else
            RealtimeEventType
            .TYPING_STOPPED
        )

        await (
            self.channel_layer
            .group_send(
                group_name,
                {
                    "type":
                        "realtime.event",
                    "source_group":
                        group_name,
                    "event":
                        build_realtime_event(
                            event_type=(
                                event_type
                            ),
                            payload={
                                "conversation_type":
                                    conversation_type,
                                "conversation_id":
                                    conversation_id,
                                "user_id":
                                    self.user.pk,
                                "username":
                                    self.user.username,
                            },
                        ),
                },
            )
        )

    async def _handle_conversation_subscribe(
        self,
        *,
        request_id: str | None,
        payload: dict[str, Any],
    ):
        parsed = self._parse_conversation(
            payload
        )

        if parsed is None:
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "A valid conversation_type "
                    "and conversation_id are required."
                ),
            )
            return

        (
            conversation_type,
            conversation_id,
        ) = parsed

        can_subscribe = await (
            self._can_subscribe(
                conversation_type=(
                    conversation_type
                ),
                conversation_id=(
                    conversation_id
                ),
            )
        )

        if not can_subscribe:
            await self._send_error(
                request_id=request_id,
                code="NOT_AUTHORIZED",
                detail=(
                    "You cannot subscribe "
                    "to this conversation."
                ),
            )
            return

        group_name = (
            conversation_group_name(
                conversation_type,
                conversation_id,
            )
        )

        await self.channel_layer.group_add(
            group_name,
            self.channel_name,
        )

        self.subscribed_groups.add(
            group_name
        )

        await self.send_json(
            build_realtime_event(
                event_type=(
                    RealtimeEventType
                    .CONVERSATION_SUBSCRIBED
                ),
                request_id=request_id,
                payload={
                    "conversation_type": (
                        conversation_type
                    ),
                    "conversation_id": (
                        conversation_id
                    ),
                },
            )
        )

    async def _handle_conversation_unsubscribe(
        self,
        *,
        request_id: str | None,
        payload: dict[str, Any],
    ):
        parsed = self._parse_conversation(
            payload
        )

        if parsed is None:
            await self._send_error(
                request_id=request_id,
                code="INVALID_COMMAND",
                detail=(
                    "A valid conversation_type "
                    "and conversation_id are required."
                ),
            )
            return

        (
            conversation_type,
            conversation_id,
        ) = parsed

        group_name = (
            conversation_group_name(
                conversation_type,
                conversation_id,
            )
        )

        await (
            self.channel_layer
            .group_discard(
                group_name,
                self.channel_name,
            )
        )

        self.subscribed_groups.discard(
            group_name
        )

        await self.send_json(
            build_realtime_event(
                event_type=(
                    RealtimeEventType
                    .CONVERSATION_UNSUBSCRIBED
                ),
                request_id=request_id,
                payload={
                    "conversation_type": (
                        conversation_type
                    ),
                    "conversation_id": (
                        conversation_id
                    ),
                },
            )
        )

    @database_sync_to_async
    def _can_subscribe(
        self,
        *,
        conversation_type: str,
        conversation_id: int,
    ) -> bool:
        return (
            RealtimeSubscriptionSelector
            .can_subscribe(
                user_id=self.user.pk,
                conversation_type=(
                    conversation_type
                ),
                conversation_id=(
                    conversation_id
                ),
            )
        )

    async def _send_error(
        self,
        *,
        code: str,
        detail: str,
        request_id: str | None,
    ):
        await self.send_json(
            build_realtime_error(
                code=code,
                detail=detail,
                request_id=request_id,
            )
        )

    @staticmethod
    def _parse_conversation(
        payload: dict[str, Any],
    ) -> tuple[str, int] | None:
        conversation_type = payload.get(
            "conversation_type"
        )
        conversation_id = payload.get(
            "conversation_id"
        )

        if conversation_type not in {
            "dm",
            "group",
        }:
            return None

        if (
            isinstance(conversation_id, bool)
            or not isinstance(
                conversation_id,
                int,
            )
            or conversation_id <= 0
        ):
            return None

        return (
            conversation_type,
            conversation_id,
        )

    @staticmethod
    def _group_id_from_source_group(
        source_group: str,
    ) -> int | None:
        prefix = "group."

        if not source_group.startswith(prefix):
            return None

        raw_group_id = source_group[len(prefix):]

        if not raw_group_id.isdigit():
            return None

        group_id = int(raw_group_id)

        if group_id <= 0:
            return None

        return group_id

    async def _discard_group_subscription(
        self,
        *,
        group_name: str,
        group_id: int,
        notify: bool,
    ) -> None:
        was_subscribed = (
            group_name
            in self.subscribed_groups
        )

        await self.channel_layer.group_discard(
            group_name,
            self.channel_name,
        )

        self.subscribed_groups.discard(
            group_name
        )

        if not notify or not was_subscribed:
            return

        await self.send_json(
            build_realtime_event(
                event_type=(
                    RealtimeEventType
                    .CONVERSATION_UNSUBSCRIBED
                ),
                payload={
                    "conversation_type": (
                        "group"
                    ),
                    "conversation_id": (
                        group_id
                    ),
                    "reason": (
                        "access_revoked"
                    ),
                },
            )
        )

    async def realtime_event(
        self,
        event: dict[str, Any],
    ):
        source_group = event.get(
            "source_group"
        )

        if isinstance(source_group, str):
            group_id = (
                self
                ._group_id_from_source_group(
                    source_group
                )
            )

            if group_id is not None:
                if (
                    source_group
                    not in self.subscribed_groups
                ):
                    # A stale Channels-group delivery can already be queued
                    # while unsubscribe/disconnect cleanup is in flight.
                    # Never forward a group-conversation event unless this
                    # consumer still considers itself subscribed.
                    await (
                        self.channel_layer
                        .group_discard(
                            source_group,
                            self.channel_name,
                        )
                    )
                    return

                can_access = await (
                    self._can_subscribe(
                        conversation_type="group",
                        conversation_id=group_id,
                    )
                )

                if not can_access:
                    # PostgreSQL membership is authoritative. This closes the
                    # short window between membership revocation and the
                    # asynchronous force-unsubscribe command being processed.
                    await self._discard_group_subscription(
                        group_name=source_group,
                        group_id=group_id,
                        notify=True,
                    )
                    return

        await self.send_json(
            event["event"]
        )

    async def realtime_force_unsubscribe(
        self,
        event: dict[str, Any],
    ):
        group_name = event["group_name"]
        conversation_type = event[
            "conversation_type"
        ]
        conversation_id = event[
            "conversation_id"
        ]

        if conversation_type == "group":
            await self._discard_group_subscription(
                group_name=group_name,
                group_id=conversation_id,
                notify=True,
            )
            return

        was_subscribed = (
            group_name
            in self.subscribed_groups
        )

        await self.channel_layer.group_discard(
            group_name,
            self.channel_name,
        )

        self.subscribed_groups.discard(
            group_name
        )

        if not was_subscribed:
            return

        await self.send_json(
            build_realtime_event(
                event_type=(
                    RealtimeEventType
                    .CONVERSATION_UNSUBSCRIBED
                ),
                payload={
                    "conversation_type": (
                        conversation_type
                    ),
                    "conversation_id": (
                        conversation_id
                    ),
                    "reason": (
                        "access_revoked"
                    ),
                },
            )
        )
