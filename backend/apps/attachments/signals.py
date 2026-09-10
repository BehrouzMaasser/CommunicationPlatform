from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.attachments.models import MessageAttachment


@receiver(
    post_delete,
    sender=MessageAttachment,
)
def delete_attachment_file_after_commit(
    sender,
    instance,
    **kwargs,
):
    """
    Delete physical storage only after the DB transaction commits.

    This matters for cascades such as group disbanding: if that transaction
    rolls back, the attachment row remains and its file must remain too.
    """
    if (
        not instance.file
        or not instance.file.name
    ):
        return

    storage = instance.file.storage
    stored_name = instance.file.name

    transaction.on_commit(
        lambda: storage.delete(stored_name)
    )
