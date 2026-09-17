from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.voice.models import VoiceRoom


@receiver(post_delete, sender=VoiceRoom)
def delete_voice_room_avatar_file(sender, instance, **kwargs):
    del sender, kwargs
    if not instance.avatar or not instance.avatar.name:
        return
    name = instance.avatar.name
    storage = instance.avatar.storage
    transaction.on_commit(lambda: storage.delete(name))
