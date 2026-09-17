from django.db import transaction
from django.urls import reverse

from apps.accounts.avatar_urls import build_avatar_url
from apps.messaging.models import Message
from apps.messaging.selectors import MessageSelector
from apps.realtime.events import RealtimeEventType
from apps.realtime.group_names import (
    conversation_group_name,
    user_group_name,
)
from apps.realtime.publisher import RealtimePublisher


def _iso(value) -> str:
    return (
        value.isoformat()
        .replace("+00:00", "Z")
    )


def _conversation_identity(
    message: Message,
) -> tuple[str, int]:
    if (
        message.direct_conversation_id
        is not None
    ):
        return (
            "dm",
            message.direct_conversation_id,
        )

    return (
        "group",
        message.group_conversation_id,
    )


class MessageRealtimePublisher:
    """
    Realtime adapter for persisted Message events.

    message.created is sent to:
      - the conversation subscription group
      - each original participant/recipient's personal user group

    The SAME event envelope/event_id is fanned out to every target, so a chat
    tab that belongs to both targets is deduplicated by RealtimeClient.
    """

    @staticmethod
    def _serialize_user(user) -> dict:
        return {
            "id": user.pk,
            "username": user.username,
            "avatar_url": build_avatar_url(
                user_id=user.pk,
                avatar_name=(
                    user.avatar.name
                    if user.avatar
                    else None
                ),
            ),
        }

    @staticmethod
    def _serialize_attachment(
        attachment,
    ) -> dict:
        return {
            "id": attachment.pk,
            "original_filename": (
                attachment.original_filename
            ),
            "mime_type": (
                attachment.mime_type
            ),
            "size_bytes": (
                attachment.size_bytes
            ),
            "created_at": _iso(
                attachment.created_at
            ),
            "download_url": reverse(
                "attachment-download",
                kwargs={
                    "attachment_id":
                        attachment.pk,
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
            "created_at": _iso(
                reply_to.created_at
            ),
        }

    @classmethod
    def _serialize_receipts(
        cls,
        message: Message,
    ) -> list[dict]:
        return [
            {
                "user":
                    cls._serialize_user(
                        receipt.user
                    ),
                "delivered_at": (
                    _iso(
                        receipt.delivered_at
                    )
                    if
                    receipt.delivered_at
                    is not None
                    else None
                ),
                "read_at": (
                    _iso(
                        receipt.read_at
                    )
                    if
                    receipt.read_at
                    is not None
                    else None
                ),
            }
            for receipt
            in message.receipts.all()
        ]

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
            "receipts":
                cls._serialize_receipts(
                    message
                ),
            "created_at": _iso(
                message.created_at
            ),
        }

    @staticmethod
    def _created_group_names(
        message: Message,
    ) -> list[str]:
        (
            conversation_type,
            conversation_id,
        ) = _conversation_identity(
            message
        )

        user_ids = {
            message.sender_id,
            *[
                receipt.user_id
                for receipt
                in message.receipts.all()
            ],
        }

        return [
            conversation_group_name(
                conversation_type,
                conversation_id,
            ),
            *[
                user_group_name(
                    user_id
                )
                for user_id
                in user_ids
            ],
        ]

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

        (
            conversation_type,
            conversation_id,
        ) = _conversation_identity(
            message
        )

        RealtimePublisher.publish(
            event_type=(
                RealtimeEventType
                .MESSAGE_CREATED
            ),
            payload={
                "conversation_type":
                    conversation_type,
                "conversation_id":
                    conversation_id,
                "message":
                    cls._serialize_message(
                        message
                    ),
            },
            group_names=(
                cls._created_group_names(
                    message
                )
            ),
        )

    @classmethod
    def publish_created_after_commit(
        cls,
        *,
        message_id: int,
    ) -> None:
        transaction.on_commit(
            lambda:
                cls._publish_created(
                    message_id=message_id,
                )
        )


class MessageReceiptRealtimePublisher:
    """
    Delivery updates go to authorized conversation subscribers. Read updates
    additionally go to the reader's personal group so other tabs can keep
    unread counters synchronized. Persistence remains the reconciliation path.
    """

    @staticmethod
    def _publish_after_commit(
        *,
        event_type: RealtimeEventType,
        message: Message,
        payload: dict,
    ) -> None:
        (
            conversation_type,
            conversation_id,
        ) = _conversation_identity(
            message
        )

        RealtimePublisher.publish_after_commit(
            event_type=event_type,
            payload={
                "conversation_type":
                    conversation_type,
                "conversation_id":
                    conversation_id,
                **payload,
            },
            group_names=[
                conversation_group_name(
                    conversation_type,
                    conversation_id,
                )
            ],
        )

    @classmethod
    def delivered_after_commit(
        cls,
        *,
        message: Message,
        user_id: int,
        delivered_at,
    ) -> None:
        cls._publish_after_commit(
            event_type=(
                RealtimeEventType
                .MESSAGE_DELIVERED
            ),
            message=message,
            payload={
                "message_id":
                    message.pk,
                "user_id":
                    user_id,
                "delivered_at":
                    _iso(delivered_at),
            },
        )

    @classmethod
    def read_after_commit(
        cls,
        *,
        message: Message,
        user_id: int,
        read_at,
        read_count: int,
    ) -> None:
        (
            conversation_type,
            conversation_id,
        ) = _conversation_identity(
            message
        )

        # Conversation subscribers need this for receipt UI. The reader's
        # personal group also receives the same event so other tabs can keep
        # navbar/unread state synchronized without polling.
        RealtimePublisher.publish_after_commit(
            event_type=(
                RealtimeEventType
                .MESSAGE_READ
            ),
            payload={
                "conversation_type":
                    conversation_type,
                "conversation_id":
                    conversation_id,
                # Read-through watermark.
                "message_id":
                    message.pk,
                "user_id":
                    user_id,
                "read_at":
                    _iso(read_at),
                "read_count":
                    read_count,
            },
            group_names=[
                conversation_group_name(
                    conversation_type,
                    conversation_id,
                ),
                user_group_name(user_id),
            ],
        )
