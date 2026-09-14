from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import (
    get_channel_layer,
)
from channels.testing import (
    WebsocketCommunicator,
)
from django.contrib.auth import (
    get_user_model,
)
from django.conf import settings
from django.test import (
    Client,
    TransactionTestCase,
    override_settings,
)

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.realtime.events import (
    build_realtime_event,
)
from apps.realtime.group_names import (
    conversation_group_name,
    user_group_name,
)
from config.asgi import application


TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": (
            "channels.layers."
            "InMemoryChannelLayer"
        ),
    }
}


@override_settings(
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS,
    ALLOWED_HOSTS=["testserver"],
)
class RealtimeConsumerTests(
    TransactionTestCase
):

    reset_sequences = True

    def setUp(self):
        User = get_user_model()

        self.alice = (
            User.objects.create_user(
                username="alice",
                email="alice@example.com",
                password="password-123",
            )
        )

        self.bob = (
            User.objects.create_user(
                username="bob",
                email="bob@example.com",
                password="password-123",
            )
        )

        self.charlie = (
            User.objects.create_user(
                username="charlie",
                email="charlie@example.com",
                password="password-123",
            )
        )

        self.dm = (
            DirectConversation.objects.create(
                user_1=self.alice,
                user_2=self.bob,
            )
        )

        self.group = (
            GroupConversation.objects.create(
                name="Study Group",
            )
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=(
                GroupMembership
                .Role
                .OWNER
            ),
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=(
                GroupMembership
                .Role
                .MEMBER
            ),
        )

    def websocket_headers_for(
        self,
        user,
    ):
        client = Client()
        client.force_login(user)

        cookie_name = (
            settings.SESSION_COOKIE_NAME
        )

        cookie = client.cookies[
            cookie_name
        ].value

        return [
            (
                b"cookie",
                (
                    f"{cookie_name}={cookie}"
                ).encode(),
            ),
            (
                b"origin",
                b"http://testserver",
            ),
            (
                b"host",
                b"testserver",
            ),
        ]

    def test_anonymous_connection_is_rejected(
        self,
    ):
        async_to_sync(
            self._assert_anonymous_rejected
        )()

    async def _assert_anonymous_rejected(
        self,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=[
                    (
                        b"origin",
                        b"http://testserver",
                    ),
                    (
                        b"host",
                        b"testserver",
                    ),
                ],
            )
        )

        connected, close_code = (
            await communicator.connect()
        )

        self.assertFalse(connected)
        self.assertEqual(
            close_code,
            4401,
        )

    def test_authenticated_connection_receives_connected_event(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_connected_event
        )(headers)

    async def _assert_connected_event(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )

        self.assertTrue(connected)

        event = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            event["type"],
            "connection.connected",
        )
        self.assertEqual(
            event["payload"][
                "user_id"
            ],
            self.alice.pk,
        )

        await communicator.disconnect()

    def test_personal_user_group_delivers_event(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_user_event
        )(headers)

    async def _assert_user_event(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        event = build_realtime_event(
            event_type=(
                "friend_request.created"
            ),
            payload={
                "request_id": 12,
            },
        )

        channel_layer = (
            get_channel_layer()
        )

        await channel_layer.group_send(
            user_group_name(
                self.alice.pk
            ),
            {
                "type": "realtime.event",
                "event": event,
            },
        )

        received = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            received,
            event,
        )

        await communicator.disconnect()

    def test_non_object_command_is_rejected(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_non_object_command_rejected
        )(headers)

    async def _assert_non_object_command_rejected(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to([])

        error = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            error["type"],
            "error",
        )
        self.assertEqual(
            error["payload"]["code"],
            "INVALID_COMMAND",
        )

        await communicator.disconnect()

    def test_boolean_conversation_id_is_rejected(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_boolean_conversation_id_rejected
        )(headers)

    async def _assert_boolean_conversation_id_rejected(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": (
                    "request-bool-conversation"
                ),
                "payload": {
                    "conversation_type": "dm",
                    "conversation_id": True,
                },
            }
        )

        error = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            error["type"],
            "error",
        )
        self.assertEqual(
            error["payload"]["code"],
            "INVALID_COMMAND",
        )

        await communicator.disconnect()

    def test_boolean_message_id_is_rejected(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_boolean_message_id_rejected
        )(headers)

    async def _assert_boolean_message_id_rejected(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": "message.delivered",
                "request_id": (
                    "request-bool-message"
                ),
                "payload": {
                    "message_id": True,
                },
            }
        )

        error = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            error["type"],
            "error",
        )
        self.assertEqual(
            error["payload"]["code"],
            "INVALID_COMMAND",
        )

        await communicator.disconnect()

    def test_dm_participant_can_subscribe(
        self,
    ):
        headers = self.websocket_headers_for(
            self.alice
        )

        async_to_sync(
            self._assert_dm_subscription
        )(headers)

    async def _assert_dm_subscription(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": "request-1",
                "payload": {
                    "conversation_type": "dm",
                    "conversation_id": (
                        self.dm.pk
                    ),
                },
            }
        )

        subscribed = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            subscribed["type"],
            "conversation.subscribed",
        )

        event = build_realtime_event(
            event_type="message.created",
            payload={"message": {"id": 99}},
        )

        channel_layer = (
            get_channel_layer()
        )

        await channel_layer.group_send(
            conversation_group_name(
                "dm",
                self.dm.pk,
            ),
            {
                "type": "realtime.event",
                "event": event,
            },
        )

        received = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            received,
            event,
        )

        await communicator.disconnect()

    def test_dm_outsider_cannot_subscribe(
        self,
    ):
        headers = self.websocket_headers_for(
            self.charlie
        )

        async_to_sync(
            self._assert_dm_outsider_denied
        )(headers)

    async def _assert_dm_outsider_denied(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": "request-2",
                "payload": {
                    "conversation_type": "dm",
                    "conversation_id": (
                        self.dm.pk
                    ),
                },
            }
        )

        error = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            error["type"],
            "error",
        )
        self.assertEqual(
            error["payload"]["code"],
            "NOT_AUTHORIZED",
        )

        await communicator.disconnect()

    def test_group_member_can_subscribe(
        self,
    ):
        headers = self.websocket_headers_for(
            self.bob
        )

        async_to_sync(
            self._assert_group_subscription
        )(headers)

    async def _assert_group_subscription(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": "request-3",
                "payload": {
                    "conversation_type": (
                        "group"
                    ),
                    "conversation_id": (
                        self.group.pk
                    ),
                },
            }
        )

        event = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            event["type"],
            "conversation.subscribed",
        )

        await communicator.disconnect()

    def test_forced_unsubscribe_removes_existing_group_subscription(
        self,
    ):
        headers = self.websocket_headers_for(
            self.bob
        )

        async_to_sync(
            self._assert_forced_unsubscribe
        )(headers)

    async def _assert_forced_unsubscribe(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": "request-force",
                "payload": {
                    "conversation_type": (
                        "group"
                    ),
                    "conversation_id": (
                        self.group.pk
                    ),
                },
            }
        )

        await communicator.receive_json_from()

        channel_layer = (
            get_channel_layer()
        )

        await channel_layer.group_send(
            user_group_name(
                self.bob.pk
            ),
            {
                "type": (
                    "realtime.force_unsubscribe"
                ),
                "group_name": (
                    conversation_group_name(
                        "group",
                        self.group.pk,
                    )
                ),
                "conversation_type": (
                    "group"
                ),
                "conversation_id": (
                    self.group.pk
                ),
            },
        )

        unsubscribed = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            unsubscribed["type"],
            "conversation.unsubscribed",
        )
        self.assertEqual(
            unsubscribed["payload"][
                "reason"
            ],
            "access_revoked",
        )

        event = build_realtime_event(
            event_type="message.created",
            payload={
                "message": {
                    "id": 101,
                }
            },
        )

        await channel_layer.group_send(
            conversation_group_name(
                "group",
                self.group.pk,
            ),
            {
                "type": "realtime.event",
                "event": event,
            },
        )

        received_nothing = (
            await communicator
            .receive_nothing(
                timeout=0.05,
            )
        )

        self.assertTrue(
            received_nothing
        )

        await communicator.disconnect()

    def test_revoked_group_member_does_not_receive_stale_group_event(
        self,
    ):
        headers = self.websocket_headers_for(
            self.bob
        )

        async_to_sync(
            self._assert_revoked_group_event_filtered
        )(headers)

    async def _assert_revoked_group_event_filtered(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": (
                    "request-race"
                ),
                "payload": {
                    "conversation_type": (
                        "group"
                    ),
                    "conversation_id": (
                        self.group.pk
                    ),
                },
            }
        )

        subscribed = (
            await communicator
            .receive_json_from()
        )
        self.assertEqual(
            subscribed["type"],
            "conversation.subscribed",
        )

        await database_sync_to_async(
            lambda: (
                GroupMembership.objects
                .filter(
                    group=self.group,
                    user=self.bob,
                )
                .delete()
            )
        )()

        group_name = (
            conversation_group_name(
                "group",
                self.group.pk,
            )
        )

        event = build_realtime_event(
            event_type="message.created",
            payload={
                "conversation_type": (
                    "group"
                ),
                "conversation_id": (
                    self.group.pk
                ),
                "message": {
                    "id": 101,
                },
            },
        )

        channel_layer = (
            get_channel_layer()
        )

        await channel_layer.group_send(
            group_name,
            {
                "type": "realtime.event",
                "event": event,
                "source_group": group_name,
            },
        )

        revoked = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            revoked["type"],
            "conversation.unsubscribed",
        )
        self.assertEqual(
            revoked["payload"][
                "reason"
            ],
            "access_revoked",
        )

        received_nothing = (
            await communicator
            .receive_nothing(
                timeout=0.05,
            )
        )
        self.assertTrue(received_nothing)

        await communicator.disconnect()

    def test_group_outsider_cannot_subscribe(
        self,
    ):
        headers = self.websocket_headers_for(
            self.charlie
        )

        async_to_sync(
            self._assert_group_outsider_denied
        )(headers)

    async def _assert_group_outsider_denied(
        self,
        headers,
    ):
        communicator = (
            WebsocketCommunicator(
                application,
                "/ws/v1/",
                headers=headers,
            )
        )

        connected, _ = (
            await communicator.connect()
        )
        self.assertTrue(connected)

        await communicator.receive_json_from()

        await communicator.send_json_to(
            {
                "type": (
                    "conversation.subscribe"
                ),
                "request_id": "request-4",
                "payload": {
                    "conversation_type": (
                        "group"
                    ),
                    "conversation_id": (
                        self.group.pk
                    ),
                },
            }
        )

        error = (
            await communicator
            .receive_json_from()
        )

        self.assertEqual(
            error["payload"]["code"],
            "NOT_AUTHORIZED",
        )

        await communicator.disconnect()
