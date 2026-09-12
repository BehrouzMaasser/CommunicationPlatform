from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.messaging.exceptions import (
    InvalidMessageContent,
    InvalidMessageContext,
    FriendshipRequiredForDirectMessage,
    MessageContextNotFound,
    ReplyMessageNotFound,
)
from apps.messaging.models import Message
from apps.messaging.realtime import MessageRealtimePublisher
from apps.messaging.services.receipt import MessageReceiptService


User = get_user_model()


class MessageService:
    """
    Message mutation rules.

    V1 messages are immutable. This service therefore creates messages but
    intentionally exposes no edit or delete operation.

    Attachment-bearing creation is added later. The internal
    _create_message_record() primitive assumes the payload has already been
    validated by its caller, so the attachment workflow can reuse it after
    validating the files and optional text together.
    """

    @staticmethod
    def _validate_context_choice(
        *,
        direct_conversation_id: int | None,
        group_id: int | None,
    ) -> None:
        has_direct_context = direct_conversation_id is not None
        has_group_context = group_id is not None

        if has_direct_context == has_group_context:
            raise InvalidMessageContext

    @staticmethod
    def _get_direct_conversation_for_update(
        *,
        current_user: User,
        conversation_id: int,
    ) -> DirectConversation:
        conversation = (
            DirectConversation.objects
            .select_for_update()
            .filter(pk=conversation_id)
            .filter(
                Q(user_1=current_user)
                | Q(user_2=current_user)
            )
            .first()
        )

        if conversation is None:
            raise MessageContextNotFound

        other_user_id = (
            conversation.user_2_id
            if conversation.user_1_id == current_user.pk
            else conversation.user_1_id
        )

        friendship_exists = Friendship.objects.filter(
            Q(
                user_1_id=current_user.pk,
                user_2_id=other_user_id,
            )
            | Q(
                user_1_id=other_user_id,
                user_2_id=current_user.pk,
            )
        ).exists()

        if not friendship_exists:
            raise FriendshipRequiredForDirectMessage

        return conversation

    @staticmethod
    def _get_group_for_update(
        *,
        current_user: User,
        group_id: int,
    ) -> GroupConversation:
        group = (
            GroupConversation.objects
            .select_for_update()
            .filter(pk=group_id)
            .first()
        )

        if group is None:
            raise MessageContextNotFound

        membership = (
            GroupMembership.objects
            .select_for_update()
            .filter(
                group=group,
                user=current_user,
            )
            .first()
        )

        if membership is None:
            raise MessageContextNotFound

        return group

    @staticmethod
    def _get_reply_target(
        *,
        reply_to_id: int | None,
        direct_conversation: DirectConversation | None,
        group_conversation: GroupConversation | None,
    ) -> Message | None:
        if reply_to_id is None:
            return None

        queryset = Message.objects.select_related(
            "sender",
        )

        if direct_conversation is not None:
            queryset = queryset.filter(
                pk=reply_to_id,
                direct_conversation=direct_conversation,
                group_conversation__isnull=True,
            )
        else:
            queryset = queryset.filter(
                pk=reply_to_id,
                direct_conversation__isnull=True,
                group_conversation=group_conversation,
            )

        reply_to = queryset.first()

        if reply_to is None:
            # Deliberately do not distinguish between an unknown message ID
            # and a message that exists in another private context.
            raise ReplyMessageNotFound

        return reply_to

    @classmethod
    def _create_message_record(
        cls,
        *,
        current_user: User,
        direct_conversation_id: int | None = None,
        group_id: int | None = None,
        content: str = "",
        reply_to_id: int | None = None,
    ) -> Message:
        """
        Internal persistence primitive.

        The caller must already have validated that the full message payload
        is meaningful. Text-only creation does that in create_text_message().
        Later, attachment-bearing creation will validate the optional text and
        files together before calling this method.
        """
        cls._validate_context_choice(
            direct_conversation_id=direct_conversation_id,
            group_id=group_id,
        )

        with transaction.atomic():
            direct_conversation = None
            group_conversation = None

            if direct_conversation_id is not None:
                direct_conversation = (
                    cls._get_direct_conversation_for_update(
                        current_user=current_user,
                        conversation_id=direct_conversation_id,
                    )
                )
            else:
                group_conversation = cls._get_group_for_update(
                    current_user=current_user,
                    group_id=group_id,
                )

            reply_to = cls._get_reply_target(
                reply_to_id=reply_to_id,
                direct_conversation=direct_conversation,
                group_conversation=group_conversation,
            )

            message = Message.objects.create(
                sender=current_user,
                direct_conversation=direct_conversation,
                group_conversation=group_conversation,
                content=content,
                reply_to=reply_to,
            )

            MessageReceiptService.initialize_for_message(
                message=message,
            )

            context = (
                direct_conversation
                if direct_conversation is not None
                else group_conversation
            )

            context.last_activity_at = message.created_at
            context.save(
                update_fields=["last_activity_at"],
            )

            MessageRealtimePublisher.publish_created_after_commit(
                message_id=message.pk,
            )

        return message

    @classmethod
    def create_text_message(
        cls,
        *,
        current_user: User,
        direct_conversation_id: int | None = None,
        group_id: int | None = None,
        content: str,
        reply_to_id: int | None = None,
    ) -> Message:
        if (
            not isinstance(content, str)
            or not content.strip()
        ):
            raise InvalidMessageContent

        # Preserve the text exactly as supplied. strip() above is validation,
        # not normalization.
        return cls._create_message_record(
            current_user=current_user,
            direct_conversation_id=direct_conversation_id,
            group_id=group_id,
            content=content,
            reply_to_id=reply_to_id,
        )
