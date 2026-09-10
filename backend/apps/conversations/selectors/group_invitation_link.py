from django.db.models import QuerySet

from apps.conversations.models import (
    GroupConversation,
    GroupInvitationLink,
)


class GroupInvitationLinkSelector:

    @staticmethod
    def list_for_group(
        *,
        group: GroupConversation,
    ) -> QuerySet[GroupInvitationLink]:
        return (
            GroupInvitationLink.objects
            .filter(group=group)
            .select_related("created_by")
            .order_by(
                "-created_at",
                "-pk",
            )
        )
