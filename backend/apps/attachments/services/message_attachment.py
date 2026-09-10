from pathlib import Path
from typing import Iterable

from django.core.files import File
from django.db import transaction

from apps.attachments.exceptions import InvalidAttachment
from apps.attachments.models import MessageAttachment
from apps.messaging.exceptions import InvalidMessageContent
from apps.messaging.models import Message
from apps.messaging.services import MessageService


class MessageAttachmentService:
    """
    Creates attachment-bearing messages atomically at the application level.

    Database writes are transactional. File storage itself is not part of the
    database transaction, so files written before a failure are explicitly
    cleaned up after rollback.
    """

    DEFAULT_MIME_TYPE = "application/octet-stream"

    @staticmethod
    def _validate_attachment(file_obj: File) -> None:
        name = getattr(file_obj, "name", None)
        size = getattr(file_obj, "size", None)

        if not isinstance(name, str) or not name:
            raise InvalidAttachment

        if (
            not isinstance(size, int)
            or size < 0
        ):
            raise InvalidAttachment

        original_filename = Path(name).name

        if (
            not original_filename
            or len(original_filename) > 255
        ):
            raise InvalidAttachment

    @classmethod
    def _create_attachment_record(
        cls,
        *,
        message: Message,
        file_obj: File,
    ) -> MessageAttachment:
        cls._validate_attachment(file_obj)

        original_filename = Path(file_obj.name).name

        declared_mime_type = getattr(
            file_obj,
            "content_type",
            None,
        )

        mime_type = (
            declared_mime_type
            if isinstance(declared_mime_type, str)
            and declared_mime_type
            else cls.DEFAULT_MIME_TYPE
        )

        if len(mime_type) > 255:
            raise InvalidAttachment

        attachment = MessageAttachment(
            message=message,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=file_obj.size,
        )

        attachment.file.save(
            original_filename,
            file_obj,
            save=False,
        )

        # FileField storage may theoretically transform the stored payload.
        # Record the size of the actual stored object when available.
        attachment.size_bytes = attachment.file.size
        attachment.save()

        return attachment

    @classmethod
    def create_message_with_attachments(
        cls,
        *,
        current_user,
        files: Iterable[File],
        direct_conversation_id: int | None = None,
        group_id: int | None = None,
        content: str = "",
        reply_to_id: int | None = None,
    ) -> Message:
        file_list = list(files)

        if not isinstance(content, str):
            raise InvalidMessageContent

        has_text = bool(content.strip())
        has_attachments = bool(file_list)

        if not has_text and not has_attachments:
            raise InvalidMessageContent(
                "A message must contain non-empty text "
                "or at least one attachment."
            )

        # Validate the complete file payload before creating the Message.
        for file_obj in file_list:
            cls._validate_attachment(file_obj)

        created_attachments = []

        try:
            with transaction.atomic():
                message = MessageService._create_message_record(
                    current_user=current_user,
                    direct_conversation_id=direct_conversation_id,
                    group_id=group_id,
                    content=content,
                    reply_to_id=reply_to_id,
                )

                for file_obj in file_list:
                    attachment = cls._create_attachment_record(
                        message=message,
                        file_obj=file_obj,
                    )
                    created_attachments.append(attachment)

        except Exception:
            # A DB rollback does not roll back external file storage.
            # Clean up only files created by this application operation.
            for attachment in created_attachments:
                if attachment.file and attachment.file.name:
                    attachment.file.delete(save=False)
            raise

        return message
