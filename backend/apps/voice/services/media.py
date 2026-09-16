from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from livekit import api

from apps.voice.exceptions import VoiceUnavailable


@dataclass(frozen=True, slots=True)
class VoiceMediaCredentials:
    server_url: str
    participant_token: str


class LiveKitMediaService:
    """Issue narrowly scoped LiveKit credentials for authorized voice sessions.

    This service deliberately knows only about media credentials. Call/group
    authorization remains in Communication Platform services and must happen
    before this service is called.
    """

    @staticmethod
    def _configuration() -> tuple[str, str, str, int]:
        if not settings.VOICE_ENABLED:
            raise VoiceUnavailable(
                "Voice communication is disabled."
            )

        server_url = settings.LIVEKIT_URL
        api_key = settings.LIVEKIT_API_KEY
        api_secret = settings.LIVEKIT_API_SECRET
        token_ttl_seconds = (
            settings.VOICE_LIVEKIT_TOKEN_TTL_SECONDS
        )

        if not server_url or not api_key or not api_secret:
            raise VoiceUnavailable(
                "Voice media infrastructure is not configured."
            )

        return (
            server_url,
            api_key,
            api_secret,
            token_ttl_seconds,
        )

    @classmethod
    def issue_join_credentials(
        cls,
        *,
        room_name: str,
        participant_identity: str,
    ) -> VoiceMediaCredentials:
        if not room_name:
            raise ValueError("room_name is required.")

        if not participant_identity:
            raise ValueError(
                "participant_identity is required."
            )

        (
            server_url,
            api_key,
            api_secret,
            token_ttl_seconds,
        ) = cls._configuration()

        token = (
            api.AccessToken(
                api_key,
                api_secret,
            )
            .with_identity(
                participant_identity
            )
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=False,
                    can_publish_sources=[
                        "microphone",
                    ],
                    can_update_own_metadata=False,
                )
            )
            .with_ttl(
                timedelta(
                    seconds=token_ttl_seconds,
                )
            )
        )

        return VoiceMediaCredentials(
            server_url=server_url,
            participant_token=token.to_jwt(),
        )
