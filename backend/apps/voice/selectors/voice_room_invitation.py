from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.voice.models import (
    VoiceRoom,
    VoiceRoomInvitation,
)


User = get_user_model()


class VoiceRoomInvitationSelector:

    @staticmethod
    def list_for_recipient(
        *,
        user: User,
    ) -> QuerySet[VoiceRoomInvitation]:
        return (
            VoiceRoomInvitation.objects
            .filter(
                recipient=user,
            )
            .select_related(
                "room",
                "room__owner",
                "invited_by",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

    @staticmethod
    def list_for_room(
        *,
        room: VoiceRoom,
    ) -> QuerySet[VoiceRoomInvitation]:
        return (
            VoiceRoomInvitation.objects
            .filter(
                room=room,
            )
            .select_related(
                "room",
                "room__owner",
                "invited_by",
                "recipient",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )
