from pathlib import Path
from uuid import UUID

from django.urls import reverse


def build_voice_room_avatar_url(
    *,
    room_id: UUID,
    avatar_name: str | None,
) -> str | None:
    if not avatar_name:
        return None

    version = Path(avatar_name).stem
    url = reverse(
        "api-voice-room-avatar",
        kwargs={
            "room_id": room_id,
        },
    )

    return f"{url}?v={version}"
