from unittest.mock import AsyncMock, Mock, patch

from django.test import SimpleTestCase, override_settings
from livekit import api

from apps.voice.exceptions import VoiceUnavailable
from apps.voice.services.media_admin import LiveKitMediaAdminService


@override_settings(
    VOICE_ENABLED=True,
    LIVEKIT_INTERNAL_URL="http://127.0.0.1:7880",
    LIVEKIT_API_KEY="devkey",
    LIVEKIT_API_SECRET="secret",
    VOICE_LIVEKIT_ADMIN_TIMEOUT_SECONDS=2,
)
class LiveKitMediaAdminServiceTests(SimpleTestCase):
    @staticmethod
    def _client_mock():
        client = Mock()
        client.room = Mock()
        client.room.remove_participant = AsyncMock()
        client.room.delete_room = AsyncMock()
        client.room.list_rooms = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @patch("apps.voice.services.media_admin.api.LiveKitAPI")
    def test_remove_participant_uses_private_api_endpoint(self, client_class):
        client = self._client_mock()
        client_class.return_value = client

        LiveKitMediaAdminService.remove_participant(
            room_name="voice_room_1",
            participant_identity="voice_participant_1",
        )

        args, kwargs = client_class.call_args
        self.assertEqual(args, ("http://127.0.0.1:7880",))
        self.assertEqual(kwargs["api_key"], "devkey")
        self.assertEqual(kwargs["api_secret"], "secret")
        self.assertFalse(kwargs["failover"])
        self.assertEqual(kwargs["timeout"].total, 2)
        request = client.room.remove_participant.await_args.args[0]
        self.assertEqual(request.room, "voice_room_1")
        self.assertEqual(request.identity, "voice_participant_1")
        client.aclose.assert_awaited_once_with()

    @patch("apps.voice.services.media_admin.api.LiveKitAPI")
    def test_delete_room_uses_room_service(self, client_class):
        client = self._client_mock()
        client_class.return_value = client

        LiveKitMediaAdminService.delete_room(room_name="voice_room_2")

        request = client.room.delete_room.await_args.args[0]
        self.assertEqual(request.room, "voice_room_2")
        client.aclose.assert_awaited_once_with()

    @patch("apps.voice.services.media_admin.api.LiveKitAPI")
    def test_missing_room_is_idempotent_cleanup(self, client_class):
        client = self._client_mock()
        client.room.delete_room.side_effect = api.ServerError(
            api.ServerErrorCode.NOT_FOUND,
            "requested room does not exist",
            status=404,
        )
        client_class.return_value = client

        LiveKitMediaAdminService.delete_room(room_name="already-gone")

        client.aclose.assert_awaited_once_with()

    @patch("apps.voice.services.media_admin.api.LiveKitAPI")
    def test_list_rooms_is_authenticated_probe(self, client_class):
        client = self._client_mock()
        expected = Mock(rooms=[])
        client.room.list_rooms.return_value = expected
        client_class.return_value = client

        result = LiveKitMediaAdminService.list_rooms()

        self.assertIs(result, expected)
        client.room.list_rooms.assert_awaited_once()
        client.aclose.assert_awaited_once_with()

    @override_settings(LIVEKIT_INTERNAL_URL="")
    def test_missing_internal_endpoint_is_rejected(self):
        with self.assertRaises(VoiceUnavailable):
            LiveKitMediaAdminService.list_rooms()

    def test_required_identifiers_are_validated(self):
        with self.assertRaises(ValueError):
            LiveKitMediaAdminService.remove_participant(
                room_name="",
                participant_identity="participant",
            )

        with self.assertRaises(ValueError):
            LiveKitMediaAdminService.remove_participant(
                room_name="room",
                participant_identity="",
            )

        with self.assertRaises(ValueError):
            LiveKitMediaAdminService.delete_room(room_name="")
