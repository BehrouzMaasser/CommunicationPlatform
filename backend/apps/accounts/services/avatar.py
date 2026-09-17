from django.conf import settings

from apps.accounts.exceptions import InvalidAvatar
from apps.avatar_images import (
    AvatarImageService,
    InvalidAvatarImage,
)


class AvatarService:
    @classmethod
    def _normalize_avatar(cls, *, file_obj):
        try:
            return AvatarImageService.normalize(
                file_obj=file_obj,
                max_size_bytes=(
                    settings.USER_AVATAR_MAX_SIZE_BYTES
                ),
                max_dimension=(
                    settings.USER_AVATAR_MAX_DIMENSION
                ),
            )
        except InvalidAvatarImage as exc:
            raise InvalidAvatar(str(exc)) from exc

    @classmethod
    def replace_avatar(
        cls,
        *,
        user,
        file_obj,
    ):
        normalized_file = cls._normalize_avatar(
            file_obj=file_obj,
        )

        return AvatarImageService.replace(
            instance=user,
            field_name="avatar",
            normalized_file=normalized_file,
        )

    @staticmethod
    def remove_avatar(*, user):
        return AvatarImageService.remove(
            instance=user,
            field_name="avatar",
        )
