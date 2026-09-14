from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.conversations.exceptions import (
    FriendshipRequiredForGroupInvitation,
    GroupInvitationAlreadyPending,
    GroupInvitationNotFound,
    GroupNotFound,
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
from apps.conversations.realtime import GroupRealtimePublisher


User = get_user_model()


class GroupInvitationService:

    @staticmethod
    def _get_invitation_group_id(
        *,
        invitation_id: int,
    ) -> int:
        try:
            return (
                GroupInvitation.objects
                .values_list("group_id", flat=True)
                .get(pk=invitation_id)
            )
        except GroupInvitation.DoesNotExist as exc:
            raise GroupInvitationNotFound from exc

    @staticmethod
    def _get_invitation_for_update(
        *,
        invitation_id: int,
    ) -> GroupInvitation:
        try:
            return (
                GroupInvitation.objects
                .select_for_update(of=("self",))
                .select_related(
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

            GroupRealtimePublisher.invitation_created_after_commit(
                invitation_id=invitation.pk,
                group_id=group.pk,
                invited_by_id=current_user.pk,
                recipient_id=target_user.pk,
            )

        return invitation

    @classmethod
    def accept_invitation(
        cls,
        *,
        current_user: User,
        invitation_id: int,
    ) -> GroupMembership:
        with transaction.atomic():
            # Resolve the parent ID without locking the child, then lock
            # parent -> child consistently with other group mutations.
            group_id = cls._get_invitation_group_id(
                invitation_id=invitation_id,
            )

            try:
                group = GroupConversationService._get_group_for_update(
                    group_id=group_id,
                )
            except GroupNotFound as exc:
                raise GroupInvitationNotFound from exc

            invitation = cls._get_invitation_for_update(
                invitation_id=invitation_id,
            )

            if invitation.recipient_id != current_user.pk:
                raise GroupInvitationRecipientRequired

            if GroupMembership.objects.filter(
                group=group,
                user=current_user,
            ).exists():
                raise UserAlreadyGroupMember

            invitation_id = invitation.pk
            invited_by_id = invitation.invited_by_id
            recipient_id = invitation.recipient_id
            recipient_username = invitation.recipient.username
            group_name = group.name

            membership = GroupConversationService._add_member(
                group=group,
                user=current_user,
            )

            invitation.delete()

            audience_user_ids = list(
                GroupMembership.objects
                .filter(group=group)
                .values_list(
                    "user_id",
                    flat=True,
                )
            )

            GroupRealtimePublisher.invitation_accepted_after_commit(
                invitation_id=invitation_id,
                group_id=group.pk,
                group_name=group_name,
                invited_by_id=invited_by_id,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
            )

            GroupRealtimePublisher.member_added_after_commit(
                group_id=group.pk,
                member_user_id=current_user.pk,
                audience_user_ids=audience_user_ids,
            )

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

            invitation_id = invitation.pk
            group_id = invitation.group_id
            invited_by_id = invitation.invited_by_id
            recipient_id = invitation.recipient_id

            invitation.delete()

            GroupRealtimePublisher.invitation_rejected_after_commit(
                invitation_id=invitation_id,
                group_id=group_id,
                invited_by_id=invited_by_id,
                recipient_id=recipient_id,
            )
