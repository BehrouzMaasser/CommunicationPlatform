import io
import warnings

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidAvatarImage(Exception):
    pass


class AvatarImageService:
    ACCEPTED_FORMATS = {
        "JPEG",
        "PNG",
        "WEBP",
    }
    OUTPUT_SIZE = (512, 512)

    @classmethod
    def normalize(
        cls,
        *,
        file_obj,
        max_size_bytes: int,
        max_dimension: int,
    ) -> ContentFile:
        size = getattr(file_obj, "size", None)

        if not isinstance(size, int) or size <= 0:
            raise InvalidAvatarImage(
                "Choose a non-empty image file."
            )

        if size > max_size_bytes:
            raise InvalidAvatarImage(
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
                    raise InvalidAvatarImage(
                        "Avatar must be a JPEG, PNG, or WebP image."
                    )

                if (
                    image.width > max_dimension
                    or image.height > max_dimension
                ):
                    raise InvalidAvatarImage(
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

        except InvalidAvatarImage:
            raise
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:
            raise InvalidAvatarImage(
                "The uploaded file is not a valid supported image."
            ) from exc

        return ContentFile(
            output.getvalue(),
            name="avatar.webp",
        )

    @staticmethod
    def replace(
        *,
        instance,
        field_name: str,
        normalized_file: ContentFile,
    ):
        image_field = getattr(instance, field_name)
        old_name = (
            image_field.name
            if image_field
            else None
        )
        storage = image_field.storage
        new_name = None

        try:
            with transaction.atomic():
                image_field.save(
                    "avatar.webp",
                    normalized_file,
                    save=False,
                )
                new_name = image_field.name
                instance.save(
                    update_fields=[field_name],
                )

                if old_name and old_name != new_name:
                    transaction.on_commit(
                        lambda: storage.delete(old_name)
                    )
        except Exception:
            if new_name:
                storage.delete(new_name)
            raise

        return instance

    @staticmethod
    def remove(
        *,
        instance,
        field_name: str,
    ):
        image_field = getattr(instance, field_name)

        if not image_field:
            return instance

        old_name = image_field.name
        storage = image_field.storage

        with transaction.atomic():
            setattr(instance, field_name, "")
            instance.save(
                update_fields=[field_name],
            )
            transaction.on_commit(
                lambda: storage.delete(old_name)
            )

        return instance
