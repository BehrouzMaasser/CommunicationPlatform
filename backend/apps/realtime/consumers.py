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

    async def receive_json(
        self,
        content: dict[str, Any],
        **kwargs,
    ):
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
            not isinstance(
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
            not isinstance(
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

    async def realtime_event(
        self,
        event: dict[str, Any],
    ):
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

        await self.channel_layer.group_discard(
            group_name,
            self.channel_name,
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
