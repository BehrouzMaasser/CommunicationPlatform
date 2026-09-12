from django.db import transaction
from django.urls import reverse

from apps.messaging.models import Message
from apps.messaging.selectors import MessageSelector
from apps.realtime.events import RealtimeEventType
from apps.realtime.group_names import conversation_group_name
from apps.realtime.publisher import RealtimePublisher


class MessageRealtimePublisher:
    """
    Realtime adapter for persisted Message events.

    The event payload is intentionally explicit rather than reusing a DRF
    serializer. Realtime is its own external contract and should not silently
    change just because a REST serializer changes later.
    """

    @staticmethod
    def _serialize_user(user) -> dict:
        return {
            "id": user.pk,
            "username": user.username,
        }

    @staticmethod
    def _serialize_attachment(attachment) -> dict:
        return {
            "id": attachment.pk,
            "original_filename": (
                attachment.original_filename
            ),
            "mime_type": attachment.mime_type,
            "size_bytes": attachment.size_bytes,
            "created_at": (
                attachment.created_at
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "download_url": reverse(
                "attachment-download",
                kwargs={
                    "attachment_id": attachment.pk,
                },
            ),
        }

    @classmethod
    def _serialize_reply(
        cls,
        reply_to: Message | None,
    ) -> dict | None:
        if reply_to is None:
            return None

        return {
            "id": reply_to.pk,
            "sender": cls._serialize_user(
                reply_to.sender
            ),
            "content": reply_to.content,
            "attachments": [
                cls._serialize_attachment(
                    attachment
                )
                for attachment
                in reply_to.attachments.all()
            ],
            "created_at": (
                reply_to.created_at
                .isoformat()
                .replace("+00:00", "Z")
            ),
        }

    @classmethod
    def _serialize_message(
        cls,
        message: Message,
    ) -> dict:
        return {
            "id": message.pk,
            "sender": cls._serialize_user(
                message.sender
            ),
            "content": message.content,
            "attachments": [
                cls._serialize_attachment(
                    attachment
                )
                for attachment
                in message.attachments.all()
            ],
            "reply_to": cls._serialize_reply(
                message.reply_to
            ),
            "created_at": (
                message.created_at
                .isoformat()
                .replace("+00:00", "Z")
            ),
        }

    @classmethod
    def _publish_created(
        cls,
        *,
        message_id: int,
    ) -> None:
        message = (
            MessageSelector
            ._base_queryset()
            .filter(pk=message_id)
            .first()
        )

        if message is None:
            return

        if (
            message.direct_conversation_id
            is not None
        ):
            conversation_type = "dm"
            conversation_id = (
                message.direct_conversation_id
            )
        else:
            conversation_type = "group"
            conversation_id = (
                message.group_conversation_id
            )

        RealtimePublisher.publish(
            event_type=(
                RealtimeEventType
                .MESSAGE_CREATED
            ),
            payload={
                "conversation_type": (
                    conversation_type
                ),
                "conversation_id": (
                    conversation_id
                ),
                "message": (
                    cls._serialize_message(
                        message
                    )
                ),
            },
            group_names=[
                conversation_group_name(
                    conversation_type,
                    conversation_id,
                )
            ],
        )

    @classmethod
    def publish_created_after_commit(
        cls,
        *,
        message_id: int,
    ) -> None:
        transaction.on_commit(
            lambda: cls._publish_created(
                message_id=message_id,
            )
        )
