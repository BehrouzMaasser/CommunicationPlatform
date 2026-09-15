from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.voice.exceptions import (
    VoiceRoomMembershipRequired,
    VoiceRoomNameRequired,
    VoiceRoomNotFound,
    VoiceRoomOwnerCannotBeRemoved,
    VoiceRoomOwnerCannotLeave,
    VoiceRoomOwnerRequired,
)
from apps.voice.models import (
    VoiceRoom,
    VoiceRoomMembership,
)


User = get_user_model()


class VoiceRoomService:

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        normalized = name.strip()

        if not normalized:
            raise VoiceRoomNameRequired

        return normalized

    @staticmethod
    def _get_room_for_update(
        *,
        room_id: UUID,
    ) -> VoiceRoom:
        try:
            return (
                VoiceRoom.objects
                .select_for_update(of=("self",))
                .get(pk=room_id)
            )
        except VoiceRoom.DoesNotExist as exc:
            raise VoiceRoomNotFound from exc

    @staticmethod
    def _require_owner(
        *,
        room: VoiceRoom,
        user: User,
    ) -> None:
        if room.owner_id != user.pk:
            raise VoiceRoomOwnerRequired

    @staticmethod
    def _get_membership_for_update(
        *,
        room: VoiceRoom,
        user: User,
    ) -> VoiceRoomMembership:
        try:
            return (
                VoiceRoomMembership.objects
                .select_for_update(of=("self",))
                .get(
                    room=room,
                    user=user,
                )
            )
        except VoiceRoomMembership.DoesNotExist as exc:
            raise VoiceRoomMembershipRequired from exc

    @classmethod
    def create_room(
        cls,
        *,
        current_user: User,
        name: str,
    ) -> VoiceRoom:
        normalized_name = cls._normalize_name(
            name,
        )

        with transaction.atomic():
            room = VoiceRoom.objects.create(
                name=normalized_name,
                owner=current_user,
            )

            VoiceRoomMembership.objects.create(
                room=room,
                user=current_user,
            )

        return room

    @classmethod
    def rename_room(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        name: str,
    ) -> VoiceRoom:
        normalized_name = cls._normalize_name(
            name,
        )

        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )

            cls._require_owner(
                room=room,
                user=current_user,
            )

            room.name = normalized_name
            room.save(
                update_fields=[
                    "name",
                    "updated_at",
                ],
            )

        return room

    @classmethod
    def leave_room(
        cls,
        *,
        current_user: User,
        room_id: UUID,
    ) -> None:
        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )

            if room.owner_id == current_user.pk:
                raise VoiceRoomOwnerCannotLeave

            membership = (
                cls._get_membership_for_update(
                    room=room,
                    user=current_user,
                )
            )

            membership.delete()

    @classmethod
    def remove_member(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        target_user: User,
    ) -> None:
        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )

            cls._require_owner(
                room=room,
                user=current_user,
            )

            if target_user.pk == room.owner_id:
                raise VoiceRoomOwnerCannotBeRemoved

            membership = (
                cls._get_membership_for_update(
                    room=room,
                    user=target_user,
                )
            )

            membership.delete()

    @classmethod
    def delete_room(
        cls,
        *,
        current_user: User,
        room_id: UUID,
    ) -> None:
        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )

            cls._require_owner(
                room=room,
                user=current_user,
            )

            room.delete()
