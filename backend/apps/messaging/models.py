from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
)


class Message(models.Model):

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    direct_conversation = models.ForeignKey(
        DirectConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )

    group_conversation = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )

    content = models.TextField(
        blank=True,
        default="",
    )

    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="replies",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        direct_conversation__isnull=False,
                        group_conversation__isnull=True,
                    )
                    | Q(
                        direct_conversation__isnull=True,
                        group_conversation__isnull=False,
                    )
                ),
                name="message_has_exactly_one_context",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "direct_conversation",
                    "created_at",
                    "id",
                ],
                name="msg_dm_created_id_idx",
            ),
            models.Index(
                fields=[
                    "group_conversation",
                    "created_at",
                    "id",
                ],
                name="msg_group_created_id_idx",
            ),
        ]

    def __str__(self):
        if self.direct_conversation_id is not None:
            context = f"DM {self.direct_conversation_id}"
        else:
            context = f"Group {self.group_conversation_id}"

        return (
            f"Message {self.pk} from "
            f"{self.sender.username} in {context}"
        )
