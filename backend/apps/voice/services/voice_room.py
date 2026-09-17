from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.avatar_images import AvatarImageService, InvalidAvatarImage
from apps.voice.exceptions import (
    InvalidVoiceRoomAvatar,
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
from apps.voice.room_realtime import (
    VoiceRoomRealtimePublisher,
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

    @staticmethod
    def _member_user_ids(
        *,
        room: VoiceRoom,
    ) -> list[int]:
        return list(
            VoiceRoomMembership.objects
            .filter(room=room)
            .order_by("user_id")
            .values_list(
                "user_id",
                flat=True,
            )
        )

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

            (
                VoiceRoomRealtimePublisher
                .room_created_after_commit(
                    room_id=room.pk,
                    room_name=room.name,
                    owner_id=current_user.pk,
                )
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

            (
                VoiceRoomRealtimePublisher
                .room_renamed_after_commit(
                    room_id=room.pk,
                    room_name=room.name,
                    audience_user_ids=(
                        cls._member_user_ids(
                            room=room,
                        )
                    ),
                )
            )

        return room


    @classmethod
    def replace_avatar(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        file_obj,
    ) -> VoiceRoom:
        try:
            room = VoiceRoom.objects.get(
                pk=room_id,
            )
        except VoiceRoom.DoesNotExist as exc:
            raise VoiceRoomNotFound from exc

        cls._require_owner(
            room=room,
            user=current_user,
        )

        try:
            normalized_file = AvatarImageService.normalize(
                file_obj=file_obj,
                max_size_bytes=settings.USER_AVATAR_MAX_SIZE_BYTES,
                max_dimension=settings.USER_AVATAR_MAX_DIMENSION,
            )
        except InvalidAvatarImage as exc:
            raise InvalidVoiceRoomAvatar(str(exc)) from exc

        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )
            cls._require_owner(
                room=room,
                user=current_user,
            )
            AvatarImageService.replace(
                instance=room,
                field_name="avatar",
                normalized_file=normalized_file,
            )
            (
                VoiceRoomRealtimePublisher
                .room_avatar_updated_after_commit(
                    room_id=room.pk,
                    audience_user_ids=(
                        cls._member_user_ids(
                            room=room,
                        )
                    ),
                )
            )

        return room

    @classmethod
    def remove_avatar(
        cls,
        *,
        current_user: User,
        room_id: UUID,
    ) -> VoiceRoom:
        with transaction.atomic():
            room = cls._get_room_for_update(
                room_id=room_id,
            )
            cls._require_owner(
                room=room,
                user=current_user,
            )
            AvatarImageService.remove(
                instance=room,
                field_name="avatar",
            )
            (
                VoiceRoomRealtimePublisher
                .room_avatar_updated_after_commit(
                    room_id=room.pk,
                    audience_user_ids=(
                        cls._member_user_ids(
                            room=room,
                        )
                    ),
                )
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

            audience_user_ids = (
                cls._member_user_ids(
                    room=room,
                )
            )

            from apps.voice.services.voice_session import (
                VoiceSessionService,
            )

            (
                VoiceSessionService
                .revoke_voice_room_participant(
                    room_id=room.pk,
                    user_id=current_user.pk,
                )
            )

            membership.delete()

            (
                VoiceRoomRealtimePublisher
                .member_left_after_commit(
                    room_id=room.pk,
                    member_user_id=current_user.pk,
                    audience_user_ids=audience_user_ids,
                )
            )

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

            audience_user_ids = (
                cls._member_user_ids(
                    room=room,
                )
            )

            from apps.voice.services.voice_session import (
                VoiceSessionService,
            )

            (
                VoiceSessionService
                .revoke_voice_room_participant(
                    room_id=room.pk,
                    user_id=target_user.pk,
                )
            )

            membership.delete()

            (
                VoiceRoomRealtimePublisher
                .member_removed_after_commit(
                    room_id=room.pk,
                    member_user_id=target_user.pk,
                    audience_user_ids=audience_user_ids,
                )
            )

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

            room_id = room.pk

            audience_user_ids = (
                cls._member_user_ids(
                    room=room,
                )
            )

            from apps.voice.services.voice_session import (
                VoiceSessionService,
            )

            (
                VoiceSessionService
                .revoke_voice_room_session(
                    room_id=room_id,
                )
            )

            room.delete()

            (
                VoiceRoomRealtimePublisher
                .room_deleted_after_commit(
                    room_id=room_id,
                    audience_user_ids=audience_user_ids,
                )
            )
