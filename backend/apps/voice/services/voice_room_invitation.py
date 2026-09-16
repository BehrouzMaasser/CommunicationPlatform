from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.friendships.selectors import FriendshipSelector
from apps.voice.exceptions import (
    UserAlreadyVoiceRoomMember,
    VoiceRoomFriendshipRequired,
    VoiceRoomInvitationAlreadyPending,
    VoiceRoomInvitationNotFound,
    VoiceRoomInvitationRecipientRequired,
    VoiceRoomInvitationTargetNotFound,
    VoiceRoomNotFound,
)
from apps.voice.models import (
    VoiceRoomInvitation,
    VoiceRoomMembership,
)
from apps.voice.room_realtime import (
    VoiceRoomRealtimePublisher,
)
from apps.voice.services.voice_room import VoiceRoomService


User = get_user_model()


class VoiceRoomInvitationService:

    @staticmethod
    def _get_invitation_room_id(
        *,
        invitation_id: UUID,
    ) -> UUID:
        try:
            return (
                VoiceRoomInvitation.objects
                .values_list(
                    "room_id",
                    flat=True,
                )
                .get(pk=invitation_id)
            )
        except VoiceRoomInvitation.DoesNotExist as exc:
            raise VoiceRoomInvitationNotFound from exc

    @staticmethod
    def _get_invitation_for_update(
        *,
        invitation_id: UUID,
    ) -> VoiceRoomInvitation:
        try:
            return (
                VoiceRoomInvitation.objects
                .select_for_update(of=("self",))
                .select_related(
                    "invited_by",
                    "recipient",
                )
                .get(pk=invitation_id)
            )
        except VoiceRoomInvitation.DoesNotExist as exc:
            raise VoiceRoomInvitationNotFound from exc

    @classmethod
    def create_invitation(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        target_user_id: int,
    ) -> VoiceRoomInvitation:
        try:
            target_user = User.objects.get(
                pk=target_user_id,
            )
        except User.DoesNotExist as exc:
            raise VoiceRoomInvitationTargetNotFound from exc

        with transaction.atomic():
            room = VoiceRoomService._get_room_for_update(
                room_id=room_id,
            )

            VoiceRoomService._require_owner(
                room=room,
                user=current_user,
            )

            if VoiceRoomMembership.objects.filter(
                room=room,
                user=target_user,
            ).exists():
                raise UserAlreadyVoiceRoomMember

            if not FriendshipSelector.exists_between_users(
                user_a=current_user,
                user_b=target_user,
            ):
                raise VoiceRoomFriendshipRequired

            if VoiceRoomInvitation.objects.filter(
                room=room,
                recipient=target_user,
            ).exists():
                raise VoiceRoomInvitationAlreadyPending

            try:
                with transaction.atomic():
                    invitation = (
                        VoiceRoomInvitation.objects.create(
                            room=room,
                            invited_by=current_user,
                            recipient=target_user,
                        )
                    )
            except IntegrityError as exc:
                if VoiceRoomInvitation.objects.filter(
                    room=room,
                    recipient=target_user,
                ).exists():
                    raise (
                        VoiceRoomInvitationAlreadyPending
                    ) from exc
                raise

            (
                VoiceRoomRealtimePublisher
                .invitation_created_after_commit(
                    invitation_id=invitation.pk,
                    room_id=room.pk,
                    room_name=room.name,
                    invited_by_id=current_user.pk,
                    recipient_id=target_user.pk,
                )
            )

        return invitation

    @classmethod
    def accept_invitation(
        cls,
        *,
        current_user: User,
        invitation_id: UUID,
    ) -> VoiceRoomMembership:
        with transaction.atomic():
            room_id = cls._get_invitation_room_id(
                invitation_id=invitation_id,
            )

            try:
                room = (
                    VoiceRoomService
                    ._get_room_for_update(
                        room_id=room_id,
                    )
                )
            except VoiceRoomNotFound as exc:
                raise VoiceRoomInvitationNotFound from exc

            invitation = (
                cls._get_invitation_for_update(
                    invitation_id=invitation_id,
                )
            )

            if (
                invitation.recipient_id
                != current_user.pk
            ):
                raise (
                    VoiceRoomInvitationRecipientRequired
                )

            if VoiceRoomMembership.objects.filter(
                room=room,
                user=current_user,
            ).exists():
                raise UserAlreadyVoiceRoomMember

            accepted_invitation_id = invitation.pk
            invited_by_id = invitation.invited_by_id
            recipient_id = invitation.recipient_id
            room_name = room.name

            membership = (
                VoiceRoomMembership.objects.create(
                    room=room,
                    user=current_user,
                )
            )

            invitation.delete()

            audience_user_ids = (
                VoiceRoomService._member_user_ids(
                    room=room,
                )
            )

            (
                VoiceRoomRealtimePublisher
                .invitation_accepted_after_commit(
                    invitation_id=accepted_invitation_id,
                    room_id=room.pk,
                    room_name=room_name,
                    invited_by_id=invited_by_id,
                    recipient_id=recipient_id,
                )
            )

            (
                VoiceRoomRealtimePublisher
                .member_added_after_commit(
                    room_id=room.pk,
                    member_user_id=current_user.pk,
                    audience_user_ids=audience_user_ids,
                )
            )

        return membership

    @classmethod
    def cancel_invitation(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        invitation_id: UUID,
    ) -> None:
        with transaction.atomic():
            invitation_room_id = (
                cls._get_invitation_room_id(
                    invitation_id=invitation_id,
                )
            )

            if invitation_room_id != room_id:
                raise VoiceRoomInvitationNotFound

            try:
                room = (
                    VoiceRoomService
                    ._get_room_for_update(
                        room_id=room_id,
                    )
                )
            except VoiceRoomNotFound as exc:
                raise VoiceRoomInvitationNotFound from exc

            VoiceRoomService._require_owner(
                room=room,
                user=current_user,
            )

            invitation = (
                cls._get_invitation_for_update(
                    invitation_id=invitation_id,
                )
            )

            if invitation.room_id != room.id:
                raise VoiceRoomInvitationNotFound

            cancelled_invitation_id = invitation.pk
            invited_by_id = invitation.invited_by_id
            recipient_id = invitation.recipient_id

            invitation.delete()

            (
                VoiceRoomRealtimePublisher
                .invitation_cancelled_after_commit(
                    invitation_id=cancelled_invitation_id,
                    room_id=room.pk,
                    invited_by_id=invited_by_id,
                    recipient_id=recipient_id,
                )
            )

    @classmethod
    def reject_invitation(
        cls,
        *,
        current_user: User,
        invitation_id: UUID,
    ) -> None:
        with transaction.atomic():
            room_id = cls._get_invitation_room_id(
                invitation_id=invitation_id,
            )

            try:
                VoiceRoomService._get_room_for_update(
                    room_id=room_id,
                )
            except VoiceRoomNotFound as exc:
                raise VoiceRoomInvitationNotFound from exc

            invitation = (
                cls._get_invitation_for_update(
                    invitation_id=invitation_id,
                )
            )

            if (
                invitation.recipient_id
                != current_user.pk
            ):
                raise (
                    VoiceRoomInvitationRecipientRequired
                )

            rejected_invitation_id = invitation.pk
            invited_by_id = invitation.invited_by_id
            recipient_id = invitation.recipient_id

            invitation.delete()

            (
                VoiceRoomRealtimePublisher
                .invitation_rejected_after_commit(
                    invitation_id=rejected_invitation_id,
                    room_id=room_id,
                    invited_by_id=invited_by_id,
                    recipient_id=recipient_id,
                )
            )
