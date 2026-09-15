from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, QuerySet

from apps.voice.models import (
    VoiceRoom,
    VoiceRoomMembership,
)


User = get_user_model()


class VoiceRoomSelector:

    @staticmethod
    def _rooms_for_user(
        *,
        user: User,
    ) -> QuerySet[VoiceRoom]:
        membership = (
            VoiceRoomMembership.objects
            .filter(
                room_id=OuterRef("pk"),
                user=user,
            )
        )

        return (
            VoiceRoom.objects
            .select_related("owner")
            .annotate(
                current_user_is_member=Exists(
                    membership,
                ),
                member_count=Count(
                    "memberships",
                    distinct=True,
                ),
            )
            .filter(
                current_user_is_member=True,
            )
        )

    @classmethod
    def list_for_user(
        cls,
        *,
        user: User,
    ) -> QuerySet[VoiceRoom]:
        return (
            cls._rooms_for_user(
                user=user,
            )
            .order_by(
                "-updated_at",
                "-created_at",
            )
        )

    @classmethod
    def get_for_member(
        cls,
        *,
        user: User,
        room_id: UUID,
    ) -> VoiceRoom | None:
        return (
            cls._rooms_for_user(
                user=user,
            )
            .filter(
                pk=room_id,
            )
            .first()
        )

    @staticmethod
    def list_members(
        *,
        room: VoiceRoom,
    ) -> QuerySet[VoiceRoomMembership]:
        return (
            VoiceRoomMembership.objects
            .filter(
                room=room,
            )
            .select_related(
                "user",
            )
            .order_by(
                "joined_at",
                "id",
            )
        )
