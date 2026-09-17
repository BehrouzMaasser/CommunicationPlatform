from pathlib import Path

from django.urls import reverse


def build_avatar_url(
    *,
    user_id: int,
    avatar_name: str | None,
) -> str | None:
    if not avatar_name:
        return None

    version = Path(avatar_name).stem
    url = reverse(
        "api-user-avatar",
        kwargs={
            "user_id": user_id,
        },
    )

    return f"{url}?v={version}"
