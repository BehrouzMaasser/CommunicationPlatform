from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)


User = get_user_model()


class GroupConversationSelector:

    @staticmethod
    def list_for_user(
        *,
        user: User,
    ) -> QuerySet[GroupConversation]:
        return (
            GroupConversation.objects
            .filter(
                memberships__user=user,
            )
            .order_by(
                "-last_activity_at",
                "-pk",
            )
        )

    @staticmethod
    def get_for_member(
        *,
        user: User,
        group_id: int,
    ) -> GroupConversation | None:
        return (
            GroupConversation.objects
            .filter(
                pk=group_id,
                memberships__user=user,
            )
            .first()
        )

    @staticmethod
    def list_members(
        *,
        group: GroupConversation,
    ) -> QuerySet[GroupMembership]:
        return (
            GroupMembership.objects
            .filter(
                group=group,
            )
            .select_related(
                "user",
            )
            .order_by(
                "joined_at",
                "pk",
            )
        )

    @staticmethod
    def get_membership(
        *,
        group: GroupConversation,
        user: User,
    ) -> GroupMembership | None:
        return (
            GroupMembership.objects
            .filter(
                group=group,
                user=user,
            )
            .select_related(
                "user",
                "group",
            )
            .first()
        )

    @staticmethod
    def is_member(
        *,
        group: GroupConversation,
        user: User,
    ) -> bool:
        return GroupMembership.objects.filter(
            group=group,
            user=user,
        ).exists()

    @staticmethod
    def is_owner(
        *,
        group: GroupConversation,
        user: User,
    ) -> bool:
        return GroupMembership.objects.filter(
            group=group,
            user=user,
            role=GroupMembership.Role.OWNER,
        ).exists()
