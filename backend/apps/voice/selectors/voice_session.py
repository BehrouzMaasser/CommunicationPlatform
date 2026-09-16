from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.voice.models import VoiceParticipation, VoiceSession


User = get_user_model()


class VoiceSessionSelector:

    @staticmethod
    def get_open_participation_for_user(
        *,
        user: User,
    ) -> VoiceParticipation | None:
        return (
            VoiceParticipation.objects
            .select_related(
                "session",
                "session__caller",
                "session__recipient",
                "session__group",
                "session__voice_room",
            )
            .filter(
                user=user,
                left_at__isnull=True,
            )
            .first()
        )

    @staticmethod
    def get_session_for_user(
        *,
        user: User,
        session_id,
    ) -> VoiceSession | None:
        return (
            VoiceSession.objects
            .filter(
                pk=session_id,
                participations__user=user,
            )
            .distinct()
            .first()
        )

    @staticmethod
    def list_open_group_participations(
        *,
        group_id: int,
    ) -> QuerySet[VoiceParticipation]:
        return (
            VoiceParticipation.objects
            .select_related(
                "user",
                "session",
            )
            .filter(
                session__group_id=group_id,
                session__kind=VoiceSession.Kind.GROUP,
                session__status=VoiceSession.Status.ACTIVE,
                left_at__isnull=True,
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

    @staticmethod
    def get_active_group_session(
        *,
        group_id: int,
    ) -> VoiceSession | None:
        return (
            VoiceSession.objects
            .filter(
                kind=VoiceSession.Kind.GROUP,
                group_id=group_id,
                status=VoiceSession.Status.ACTIVE,
            )
            .first()
        )

    @staticmethod
    def list_open_room_participations(
        *,
        room_id,
    ) -> QuerySet[VoiceParticipation]:
        return (
            VoiceParticipation.objects
            .select_related(
                "user",
                "session",
            )
            .filter(
                session__voice_room_id=room_id,
                session__kind=VoiceSession.Kind.ROOM,
                session__status=VoiceSession.Status.ACTIVE,
                left_at__isnull=True,
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

    @staticmethod
    def get_active_room_session(
        *,
        room_id,
    ) -> VoiceSession | None:
        return (
            VoiceSession.objects
            .filter(
                kind=VoiceSession.Kind.ROOM,
                voice_room_id=room_id,
                status=VoiceSession.Status.ACTIVE,
            )
            .first()
        )

    @staticmethod
    def list_open_participations_for_session(
        *,
        session: VoiceSession,
    ) -> QuerySet[VoiceParticipation]:
        return (
            VoiceParticipation.objects
            .select_related("user")
            .filter(
                session=session,
                left_at__isnull=True,
            )
            .order_by("created_at", "pk")
        )
