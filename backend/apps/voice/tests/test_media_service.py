from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.voice.exceptions import VoiceUnavailable
from apps.voice.services.media import LiveKitMediaService


class LiveKitMediaServiceTests(SimpleTestCase):

    @override_settings(
        VOICE_ENABLED=False,
        LIVEKIT_URL="",
        LIVEKIT_API_KEY="",
        LIVEKIT_API_SECRET="",
        VOICE_LIVEKIT_TOKEN_TTL_SECONDS=300,
    )
    def test_credentials_are_not_issued_when_voice_is_disabled(self):
        with self.assertRaises(VoiceUnavailable):
            LiveKitMediaService.issue_join_credentials(
                room_name="voice-room",
                participant_identity="participant-1",
            )

    @override_settings(
        VOICE_ENABLED=True,
        LIVEKIT_URL="ws://127.0.0.1:7880",
        LIVEKIT_API_KEY="devkey",
        LIVEKIT_API_SECRET="secret",
        VOICE_LIVEKIT_TOKEN_TTL_SECONDS=300,
    )
    @patch("apps.voice.services.media.api.VideoGrants")
    @patch("apps.voice.services.media.api.AccessToken")
    def test_join_token_is_audio_only_and_short_lived(
        self,
        access_token_class,
        video_grants_class,
    ):
        token = Mock()
        access_token_class.return_value = token

        token.with_identity.return_value = token
        token.with_grants.return_value = token
        token.with_ttl.return_value = token
        token.to_jwt.return_value = "signed-token"

        grants = Mock()
        video_grants_class.return_value = grants

        credentials = (
            LiveKitMediaService.issue_join_credentials(
                room_name="voice-room-123",
                participant_identity="voice-user-123",
            )
        )

        access_token_class.assert_called_once_with(
            "devkey",
            "secret",
        )
        token.with_identity.assert_called_once_with(
            "voice-user-123"
        )
        video_grants_class.assert_called_once_with(
            room_join=True,
            room="voice-room-123",
            can_publish=True,
            can_subscribe=True,
            can_publish_data=False,
            can_publish_sources=[
                "microphone",
            ],
            can_update_own_metadata=False,
        )
        token.with_grants.assert_called_once_with(
            grants
        )
        token.with_ttl.assert_called_once_with(
            timedelta(seconds=300)
        )

        self.assertEqual(
            credentials.server_url,
            "ws://127.0.0.1:7880",
        )
        self.assertEqual(
            credentials.participant_token,
            "signed-token",
        )

    @override_settings(
        VOICE_ENABLED=True,
        LIVEKIT_URL="",
        LIVEKIT_API_KEY="devkey",
        LIVEKIT_API_SECRET="secret",
        VOICE_LIVEKIT_TOKEN_TTL_SECONDS=300,
    )
    def test_missing_livekit_configuration_is_rejected(self):
        with self.assertRaises(VoiceUnavailable):
            LiveKitMediaService.issue_join_credentials(
                room_name="voice-room",
                participant_identity="participant-1",
            )

    @override_settings(
        VOICE_ENABLED=True,
        LIVEKIT_URL="ws://127.0.0.1:7880",
        LIVEKIT_API_KEY="devkey",
        LIVEKIT_API_SECRET="secret",
        VOICE_LIVEKIT_TOKEN_TTL_SECONDS=300,
    )
    def test_room_name_and_identity_are_required(self):
        with self.assertRaises(ValueError):
            LiveKitMediaService.issue_join_credentials(
                room_name="",
                participant_identity="participant-1",
            )

        with self.assertRaises(ValueError):
            LiveKitMediaService.issue_join_credentials(
                room_name="voice-room",
                participant_identity="",
            )
