from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.test import SimpleTestCase, override_settings

from apps.realtime.group_names import conversation_group_name
from apps.realtime.publisher import RealtimePublisher


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
)
class RealtimePublisherTests(SimpleTestCase):

    def test_publish_includes_internal_source_group(self):
        channel_layer = get_channel_layer()
        channel_name = async_to_sync(
            channel_layer.new_channel
        )()
        group_name = conversation_group_name(
            "group",
            7,
        )

        async_to_sync(
            channel_layer.group_add
        )(
            group_name,
            channel_name,
        )

        RealtimePublisher.publish(
            event_type="group.renamed",
            payload={
                "group_id": 7,
                "name": "Updated",
            },
            group_names=[group_name],
        )

        delivered = async_to_sync(
            channel_layer.receive
        )(channel_name)

        self.assertEqual(
            delivered["type"],
            "realtime.event",
        )
        self.assertEqual(
            delivered["source_group"],
            group_name,
        )
        self.assertEqual(
            delivered["event"]["type"],
            "group.renamed",
        )
