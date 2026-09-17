from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.conversations.models import GroupConversation


@receiver(post_delete, sender=GroupConversation)
def delete_group_avatar_file(sender, instance, **kwargs):
    del sender, kwargs
    if not instance.avatar or not instance.avatar.name:
        return
    name = instance.avatar.name
    storage = instance.avatar.storage
    transaction.on_commit(lambda: storage.delete(name))
