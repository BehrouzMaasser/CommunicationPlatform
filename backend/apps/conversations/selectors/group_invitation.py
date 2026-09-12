from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.conversations.models import GroupInvitation


User = get_user_model()


class GroupInvitationSelector:

    @staticmethod
    def list_incoming(
        *,
        user: User,
    ) -> QuerySet[GroupInvitation]:
        return (
            GroupInvitation.objects
            .filter(recipient=user)
            .select_related(
                "group",
                "invited_by",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-pk",
            )
        )


    @staticmethod
    def list_for_group(
        *,
        group_id: int,
    ) -> QuerySet[GroupInvitation]:
        return (
            GroupInvitation.objects
            .filter(group_id=group_id)
            .select_related(
                "group",
                "invited_by",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-pk",
            )
        )

    @staticmethod
    def get_for_recipient(
        *,
        user: User,
        invitation_id: int,
    ) -> GroupInvitation | None:
        return (
            GroupInvitation.objects
            .filter(
                pk=invitation_id,
                recipient=user,
            )
            .select_related(
                "group",
                "invited_by",
                "recipient",
            )
            .first()
        )

    @staticmethod
    def pending_exists(
        *,
        group_id: int,
        user: User,
    ) -> bool:
        return GroupInvitation.objects.filter(
            group_id=group_id,
            recipient=user,
        ).exists()
