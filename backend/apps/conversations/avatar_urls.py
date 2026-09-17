from pathlib import Path

from django.urls import reverse


def build_group_avatar_url(
    *,
    group_id: int,
    avatar_name: str | None,
) -> str | None:
    if not avatar_name:
        return None

    version = Path(avatar_name).stem
    url = reverse(
        "api-group-avatar",
        kwargs={
            "group_id": group_id,
        },
    )

    return f"{url}?v={version}"
