from django.db.models import Q, QuerySet

from apps.attachments.models import MessageAttachment


class MessageAttachmentSelector:

    @staticmethod
    def list_for_message(
        *,
        message,
    ) -> QuerySet[MessageAttachment]:
        return (
            MessageAttachment.objects
            .filter(message=message)
            .order_by(
                "created_at",
                "pk",
            )
        )

    @staticmethod
    def get_for_user(
        *,
        user,
        attachment_id: int,
    ) -> MessageAttachment | None:
        return (
            MessageAttachment.objects
            .select_related(
                "message",
                "message__sender",
                "message__direct_conversation",
                "message__group_conversation",
            )
            .filter(pk=attachment_id)
            .filter(
                Q(
                    message__direct_conversation__user_1=user,
                )
                | Q(
                    message__direct_conversation__user_2=user,
                )
                | Q(
                    message__group_conversation__memberships__user=user,
                )
            )
            .distinct()
            .first()
        )
