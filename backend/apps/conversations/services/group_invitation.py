from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.conversations.exceptions import (
    FriendshipRequiredForGroupInvitation,
    GroupInvitationAlreadyPending,
    GroupInvitationNotFound,
    GroupInvitationRecipientRequired,
    GroupInvitationTargetNotFound,
    UserAlreadyGroupMember,
)
from apps.conversations.models import (
    GroupInvitation,
    GroupMembership,
)
from apps.conversations.services.group_conversation import (
    GroupConversationService,
)
from apps.friendships.selectors import FriendshipSelector


User = get_user_model()


class GroupInvitationService:

    @staticmethod
    def _get_invitation_for_update(
        *,
        invitation_id: int,
    ) -> GroupInvitation:
        try:
            return (
                GroupInvitation.objects
                .select_for_update()
                .select_related(
                    "group",
                    "invited_by",
                    "recipient",
                )
                .get(pk=invitation_id)
            )
        except GroupInvitation.DoesNotExist as exc:
            raise GroupInvitationNotFound from exc

    @classmethod
    def create_invitation(
        cls,
        *,
        current_user: User,
        group_id: int,
        target_user_id: int,
    ) -> GroupInvitation:
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist as exc:
            raise GroupInvitationTargetNotFound from exc

        with transaction.atomic():
            group = GroupConversationService._get_group_for_update(
                group_id=group_id,
            )

            GroupConversationService._require_owner(
                group=group,
                user=current_user,
            )

            if GroupMembership.objects.filter(
                group=group,
                user=target_user,
            ).exists():
                raise UserAlreadyGroupMember

            if not FriendshipSelector.exists_between_users(
                user_a=current_user,
                user_b=target_user,
            ):
                raise FriendshipRequiredForGroupInvitation

            if GroupInvitation.objects.filter(
                group=group,
                recipient=target_user,
            ).exists():
                raise GroupInvitationAlreadyPending

            try:
                with transaction.atomic():
                    invitation = GroupInvitation.objects.create(
                        group=group,
                        invited_by=current_user,
                        recipient=target_user,
                    )
            except IntegrityError as exc:
                if GroupInvitation.objects.filter(
                    group=group,
                    recipient=target_user,
                ).exists():
                    raise GroupInvitationAlreadyPending from exc
                raise

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupInvitationCreated(...)
            # )

        return invitation

    @classmethod
    def accept_invitation(
        cls,
        *,
        current_user: User,
        invitation_id: int,
    ) -> GroupMembership:
        with transaction.atomic():
            invitation = cls._get_invitation_for_update(
                invitation_id=invitation_id,
            )

            if invitation.recipient_id != current_user.pk:
                raise GroupInvitationRecipientRequired

            group = GroupConversationService._get_group_for_update(
                group_id=invitation.group_id,
            )

            if GroupMembership.objects.filter(
                group=group,
                user=current_user,
            ).exists():
                raise UserAlreadyGroupMember

            membership = GroupConversationService._add_member(
                group=group,
                user=current_user,
            )

            invitation.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupInvitationAccepted(...)
            # )

        return membership

    @classmethod
    def reject_invitation(
        cls,
        *,
        current_user: User,
        invitation_id: int,
    ) -> None:
        with transaction.atomic():
            invitation = cls._get_invitation_for_update(
                invitation_id=invitation_id,
            )

            if invitation.recipient_id != current_user.pk:
                raise GroupInvitationRecipientRequired

            invitation.delete()

            # Later:
            # transaction.on_commit(
            #     lambda: publish GroupInvitationRejected(...)
            # )
