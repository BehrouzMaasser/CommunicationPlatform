from django.test import SimpleTestCase

from apps.realtime.consumers import RealtimeConsumer


class RealtimeEphemeralConsumerRegressionTests(
    SimpleTestCase
):

    def test_presence_and_typing_handlers_exist(self):
        required_handlers = {
            "_broadcast_presence",
            "_send_presence_snapshot",
            "_handle_presence_heartbeat",
            "_handle_typing",
            "_friend_user_ids",
            "_can_publish_typing",
        }

        missing = {
            handler
            for handler in required_handlers
            if not hasattr(
                RealtimeConsumer,
                handler,
            )
        }

        self.assertEqual(
            missing,
            set(),
        )

    def test_presence_expiry_is_serialized_as_utc_iso(self):
        value = (
            RealtimeConsumer
            ._expires_at_iso(
                0.0,
            )
        )

        self.assertEqual(
            value,
            "1970-01-01T00:00:00Z",
        )
