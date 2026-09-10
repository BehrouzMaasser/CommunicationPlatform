import uuid

from django.db import models

from apps.messaging.models import Message


def message_attachment_upload_to(instance, filename):
    """
    Keep user-controlled filenames out of the storage path.

    The original filename is stored separately as metadata and is used later
    for the authorized download response.
    """
    return (
        f"message_attachments/"
        f"{instance.message_id}/"
        f"{uuid.uuid4().hex}"
    )


class MessageAttachment(models.Model):

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to=message_attachment_upload_to,
        max_length=500,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    mime_type = models.CharField(
        max_length=255,
    )

    size_bytes = models.PositiveBigIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"Attachment {self.pk} "
            f"for message {self.message_id}"
        )
