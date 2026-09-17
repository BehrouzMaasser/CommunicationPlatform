from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.accounts.models import User


@receiver(post_delete, sender=User)
def delete_user_avatar_file(
    sender,
    instance,
    **kwargs,
):
    del sender, kwargs

    if not instance.avatar or not instance.avatar.name:
        return

    name = instance.avatar.name
    storage = instance.avatar.storage

    transaction.on_commit(
        lambda: storage.delete(name)
    )
