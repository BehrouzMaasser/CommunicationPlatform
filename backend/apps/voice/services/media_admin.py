import aiohttp
from asgiref.sync import async_to_sync
from django.conf import settings
from livekit import api

from apps.voice.exceptions import VoiceUnavailable


class LiveKitMediaAdminService:
    """Administrative control of the self-hosted LiveKit media server.

    The browser-facing WebSocket URL and the server-to-server API URL are kept
    separate deliberately. Production Django should call the local/private
    LiveKit endpoint so participant revocation does not depend on public DNS,
    TLS, or Nginx being healthy.
    """

    @staticmethod
    def _configuration() -> tuple[str, str, str, int]:
        internal_url = settings.LIVEKIT_INTERNAL_URL
        api_key = settings.LIVEKIT_API_KEY
        api_secret = settings.LIVEKIT_API_SECRET
        timeout_seconds = settings.VOICE_LIVEKIT_ADMIN_TIMEOUT_SECONDS

        if not internal_url or not api_key or not api_secret:
            raise VoiceUnavailable(
                "Voice media administration is not configured."
            )

        return internal_url, api_key, api_secret, timeout_seconds

    @classmethod
    def _client(cls) -> api.LiveKitAPI:
        internal_url, api_key, api_secret, timeout_seconds = cls._configuration()
        return api.LiveKitAPI(
            internal_url,
            api_key=api_key,
            api_secret=api_secret,
            timeout=aiohttp.ClientTimeout(total=timeout_seconds),
            failover=False,
        )

    @classmethod
    async def _remove_participant_async(
        cls,
        *,
        room_name: str,
        participant_identity: str,
    ) -> None:
        client = cls._client()
        try:
            try:
                await client.room.remove_participant(
                    api.RoomParticipantIdentity(
                        room=room_name,
                        identity=participant_identity,
                    )
                )
            except api.ServerError as exc:
                if exc.code != api.ServerErrorCode.NOT_FOUND:
                    raise
        finally:
            await client.aclose()

    @classmethod
    def remove_participant(
        cls,
        *,
        room_name: str,
        participant_identity: str,
    ) -> None:
        if not room_name:
            raise ValueError("room_name is required.")
        if not participant_identity:
            raise ValueError("participant_identity is required.")

        async_to_sync(cls._remove_participant_async)(
            room_name=room_name,
            participant_identity=participant_identity,
        )

    @classmethod
    async def _delete_room_async(cls, *, room_name: str) -> None:
        client = cls._client()
        try:
            try:
                await client.room.delete_room(
                    api.DeleteRoomRequest(room=room_name)
                )
            except api.ServerError as exc:
                if exc.code != api.ServerErrorCode.NOT_FOUND:
                    raise
        finally:
            await client.aclose()

    @classmethod
    def delete_room(cls, *, room_name: str) -> None:
        if not room_name:
            raise ValueError("room_name is required.")

        async_to_sync(cls._delete_room_async)(room_name=room_name)

    @classmethod
    async def _list_rooms_async(cls):
        client = cls._client()
        try:
            return await client.room.list_rooms(api.ListRoomsRequest())
        finally:
            await client.aclose()

    @classmethod
    def list_rooms(cls):
        """Small authenticated probe used by deployment checks."""

        return async_to_sync(cls._list_rooms_async)()
