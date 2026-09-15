import logging
from collections.abc import Callable

from django.conf import settings
from django.db import transaction

from apps.voice.services.media_admin import LiveKitMediaAdminService


logger = logging.getLogger(__name__)


class VoiceMediaCleanup:
    """Schedule best-effort media revocation after database commits.

    PostgreSQL remains authoritative. A LiveKit outage must never prevent a
    friendship/group/domain mutation from committing. In production LiveKit is
    reached over localhost, so a failed cleanup normally also means the media
    process itself is unavailable.
    """

    @staticmethod
    def _best_effort(callback: Callable[[], None], *, description: str) -> None:
        if not settings.VOICE_ENABLED:
            return

        try:
            callback()
        except Exception:
            logger.exception("LiveKit cleanup failed: %s", description)

    @classmethod
    def remove_participant_after_commit(
        cls,
        *,
        room_name: str,
        participant_identity: str,
    ) -> None:
        def cleanup() -> None:
            cls._best_effort(
                lambda: LiveKitMediaAdminService.remove_participant(
                    room_name=room_name,
                    participant_identity=participant_identity,
                ),
                description=(
                    f"remove participant {participant_identity} "
                    f"from {room_name}"
                ),
            )

        transaction.on_commit(cleanup)

    @classmethod
    def delete_room_after_commit(cls, *, room_name: str) -> None:
        def cleanup() -> None:
            cls._best_effort(
                lambda: LiveKitMediaAdminService.delete_room(
                    room_name=room_name,
                ),
                description=f"delete room {room_name}",
            )

        transaction.on_commit(cleanup)
