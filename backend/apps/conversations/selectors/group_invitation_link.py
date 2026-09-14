from django.db.models import QuerySet
from django.utils import timezone

from apps.conversations.models import (
    GroupConversation,
    GroupInvitationLink,
)


class GroupInvitationLinkSelector:


    @staticmethod
    def list_active_for_group(
        *,
        group: GroupConversation,
    ) -> QuerySet[GroupInvitationLink]:
        return (
            GroupInvitationLink.objects
            .filter(
                group=group,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related("created_by")
            .order_by(
                "-created_at",
                "-pk",
            )
        )

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
