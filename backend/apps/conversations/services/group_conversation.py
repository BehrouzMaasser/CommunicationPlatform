from django.contrib.auth import get_user_model
from django.db import transaction

from apps.conversations.exceptions import (
    GroupMembershipNotFound,
    GroupNotFound,
    GroupOwnerCannotBeRemoved,
    GroupOwnerRequired,
    InvalidGroupName,
    UserAlreadyGroupMember,
)
from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)


User = get_user_model()


class GroupConversationService:

    @staticmethod
    def _get_group_for_update(
        *,
        group_id: int,
    ) -> GroupConversation:
        try:
            return (
                GroupConversation.objects
                .select_for_update()
                .get(pk=group_id)
            )
        except GroupConversation.DoesNotExist as exc:
            raise GroupNotFound from exc

    @staticmethod
    def _require_owner(
        *,
        group: GroupConversation,
        user: User,
    ) -> GroupMembership:
        try:
            return GroupMembership.objects.get(
                group=group,
                user=user,
                role=GroupMembership.Role.OWNER,
            )
        except GroupMembership.DoesNotExist as exc:
            raise GroupOwnerRequired from exc

    @classmethod
    def create_group(
        cls,
        *,
        current_user: User,
        name: str,
    ) -> GroupConversation:
        if not name or not name.strip():
            raise InvalidGroupName

        with transaction.atomic():
            group = GroupConversation.objects.create(
                name=name,
            )

            GroupMembership.objects.create(
                group=group,
                user=current_user,
                role=GroupMembership.Role.OWNER,
            )

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupCreated(...)
            # )

        return group

    @classmethod
    def _add_member(
        cls,
        *,
        group: GroupConversation,
        user: User,
    ) -> GroupMembership:
        """
        Internal operation.

        Joining a group is not a standalone V1 user action.
        Membership will later be granted by a validated invitation
        or invitation-link workflow.
        """

        membership, created = (
            GroupMembership.objects.get_or_create(
                group=group,
                user=user,
                defaults={
                    "role": GroupMembership.Role.MEMBER,
                },
            )
        )

        if not created:
            raise UserAlreadyGroupMember

        return membership

    @classmethod
    def rename_group(
        cls,
        *,
        current_user: User,
        group_id: int,
        name: str,
    ) -> GroupConversation:
        if not name or not name.strip():
            raise InvalidGroupName

        with transaction.atomic():
            group = cls._get_group_for_update(
                group_id=group_id,
            )

            cls._require_owner(
                group=group,
                user=current_user,
            )

            group.name = name
            group.save(
                update_fields=["name"],
            )

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupUpdated(...)
            # )

        return group

    @classmethod
    def remove_member(
        cls,
        *,
        current_user: User,
        group_id: int,
        member_user_id: int,
    ) -> None:
        with transaction.atomic():
            group = cls._get_group_for_update(
                group_id=group_id,
            )

            cls._require_owner(
                group=group,
                user=current_user,
            )

            try:
                membership = (
                    GroupMembership.objects
                    .select_for_update()
                    .get(
                        group=group,
                        user_id=member_user_id,
                    )
                )
            except GroupMembership.DoesNotExist as exc:
                raise GroupMembershipNotFound from exc

            if membership.role == GroupMembership.Role.OWNER:
                raise GroupOwnerCannotBeRemoved

            membership.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupMemberRemoved(...)
            # )

    @classmethod
    def leave_group(
        cls,
        *,
        current_user: User,
        group_id: int,
    ) -> None:
        with transaction.atomic():
            group = cls._get_group_for_update(
                group_id=group_id,
            )

            try:
                membership = (
                    GroupMembership.objects
                    .select_for_update()
                    .get(
                        group=group,
                        user=current_user,
                    )
                )
            except GroupMembership.DoesNotExist as exc:
                raise GroupMembershipNotFound from exc

            if membership.role == GroupMembership.Role.OWNER:
                cls._disband_group(group=group)
                return

            membership.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupMemberLeft(...)
            # )

    @classmethod
    def disband_group(
        cls,
        *,
        current_user: User,
        group_id: int,
    ) -> None:
        with transaction.atomic():
            group = cls._get_group_for_update(
                group_id=group_id,
            )

            cls._require_owner(
                group=group,
                user=current_user,
            )

            cls._disband_group(group=group)

    @staticmethod
    def _disband_group(
            *,
            group: GroupConversation,
    ) -> None:
        """
        Internal group-deletion primitive.

        The caller must already have validated that disbanding
        is allowed.
        """

        group.delete()

        # Later:
        # transaction.on_commit(
        #     lambda: publish GroupDeleted(...)
        # )