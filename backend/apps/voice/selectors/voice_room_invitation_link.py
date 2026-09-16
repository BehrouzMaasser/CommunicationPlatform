from django.db.models import QuerySet
from django.utils import timezone

from apps.voice.models import (
    VoiceRoom,
    VoiceRoomInvitationLink,
)


class VoiceRoomInvitationLinkSelector:

    @staticmethod
    def list_active_for_room(
        *,
        room: VoiceRoom,
    ) -> QuerySet[VoiceRoomInvitationLink]:
        return (
            VoiceRoomInvitationLink.objects
            .filter(
                room=room,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related(
                "room",
                "created_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )
