import io
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.exceptions import InvalidAvatar


class AvatarService:
    ACCEPTED_FORMATS = {
        "JPEG",
        "PNG",
        "WEBP",
    }

    OUTPUT_SIZE = (512, 512)

    @classmethod
    def _normalize_avatar(cls, *, file_obj) -> ContentFile:
        size = getattr(file_obj, "size", None)

        if (
            not isinstance(size, int)
            or size <= 0
        ):
            raise InvalidAvatar(
                "Choose a non-empty image file."
            )

        if size > settings.USER_AVATAR_MAX_SIZE_BYTES:
            raise InvalidAvatar(
                "Avatar exceeds the maximum allowed file size."
            )

        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error",
                    Image.DecompressionBombWarning,
                )

                image = Image.open(file_obj)
                source_format = image.format

                if source_format not in cls.ACCEPTED_FORMATS:
                    raise InvalidAvatar(
                        "Avatar must be a JPEG, PNG, or WebP image."
                    )

                if (
                    image.width > settings.USER_AVATAR_MAX_DIMENSION
                    or image.height > settings.USER_AVATAR_MAX_DIMENSION
                ):
                    raise InvalidAvatar(
                        "Avatar dimensions are too large."
                    )

                image.load()

            image = ImageOps.exif_transpose(image)

            has_alpha = (
                "A" in image.getbands()
                or "transparency" in image.info
            )

            image = image.convert(
                "RGBA" if has_alpha else "RGB"
            )

            image = ImageOps.fit(
                image,
                cls.OUTPUT_SIZE,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

            output = io.BytesIO()
            image.save(
                output,
                format="WEBP",
                quality=85,
                method=6,
            )

        except InvalidAvatar:
            raise
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:
            raise InvalidAvatar(
                "The uploaded file is not a valid supported image."
            ) from exc

        return ContentFile(
            output.getvalue(),
            name="avatar.webp",
        )

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

        old_name = (
            user.avatar.name
            if user.avatar
            else None
        )
        storage = user.avatar.storage
        new_name = None

        try:
            with transaction.atomic():
                user.avatar.save(
                    "avatar.webp",
                    normalized_file,
                    save=False,
                )
                new_name = user.avatar.name
                user.save(
                    update_fields=["avatar"],
                )

                if old_name and old_name != new_name:
                    transaction.on_commit(
                        lambda: storage.delete(old_name)
                    )
        except Exception:
            if new_name:
                storage.delete(new_name)
            raise

        return user

    @staticmethod
    def remove_avatar(*, user):
        if not user.avatar:
            return user

        old_name = user.avatar.name
        storage = user.avatar.storage

        with transaction.atomic():
            user.avatar = ""
            user.save(
                update_fields=["avatar"],
            )
            transaction.on_commit(
                lambda: storage.delete(old_name)
            )

        return user
