from django.contrib.auth import get_user_model
from django.db import transaction

from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)
from apps.voice.exceptions import (
    VoiceGroupMembershipRequired,
    VoiceInvalidState,
    VoiceParticipationClaimed,
    VoiceParticipationNotActive,
    VoiceRoomMembershipRequired,
    VoiceSessionNotFound,
)
from apps.voice.models import (
    VoiceParticipation,
    VoiceRoom,
    VoiceRoomMembership,
    VoiceSession,
)
from apps.voice.services.media import (
    LiveKitMediaService,
    VoiceMediaCredentials,
)
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


class VoiceMediaAccessService:
    """Authorize application state before issuing LiveKit credentials."""

    @staticmethod
    def _require_active_participation(
        *,
        session: VoiceSession,
        current_user: User,
        client_instance_id,
    ) -> VoiceParticipation:
        if session.status != VoiceSession.Status.ACTIVE:
            raise VoiceInvalidState

        participation = (
            VoiceParticipation.objects
            .select_for_update()
            .filter(
                session=session,
                user=current_user,
                left_at__isnull=True,
            )
            .first()
        )

        if participation is None:
            raise VoiceParticipationNotActive

        if participation.client_instance_id != client_instance_id:
            raise VoiceParticipationClaimed

        return participation

    @classmethod
    def issue_credentials(
        cls,
        *,
        current_user: User,
        session_id,
        client_instance_id,
    ) -> VoiceMediaCredentials:
        client_instance_id = VoiceSessionService.normalize_client_instance_id(
            client_instance_id
        )

        snapshot = (
            VoiceSession.objects
            .filter(pk=session_id)
            .values(
                "kind",
                "group_id",
                "voice_room_id",
            )
            .first()
        )

        if snapshot is None:
            raise VoiceSessionNotFound

        with transaction.atomic():
            if snapshot["kind"] == VoiceSession.Kind.GROUP:
                group = (
                    GroupConversation.objects
                    .select_for_update()
                    .filter(pk=snapshot["group_id"])
                    .first()
                )

                if group is None:
                    raise VoiceSessionNotFound

                membership = (
                    GroupMembership.objects
                    .select_for_update()
                    .filter(
                        group=group,
                        user=current_user,
                    )
                    .first()
                )

                if membership is None:
                    raise VoiceGroupMembershipRequired

                session = (
                    VoiceSession.objects
                    .select_for_update()
                    .filter(
                        pk=session_id,
                        kind=VoiceSession.Kind.GROUP,
                        group=group,
                    )
                    .first()
                )

            elif snapshot["kind"] == VoiceSession.Kind.ROOM:
                room = (
                    VoiceRoom.objects
                    .select_for_update()
                    .filter(
                        pk=snapshot["voice_room_id"]
                    )
                    .first()
                )

                if room is None:
                    raise VoiceSessionNotFound

                membership = (
                    VoiceRoomMembership.objects
                    .select_for_update()
                    .filter(
                        room=room,
                        user=current_user,
                    )
                    .first()
                )

                if membership is None:
                    raise VoiceRoomMembershipRequired

                session = (
                    VoiceSession.objects
                    .select_for_update()
                    .filter(
                        pk=session_id,
                        kind=VoiceSession.Kind.ROOM,
                        voice_room=room,
                    )
                    .first()
                )

            elif snapshot["kind"] == VoiceSession.Kind.DIRECT:
                session = (
                    VoiceSession.objects
                    .select_for_update()
                    .filter(
                        pk=session_id,
                        kind=VoiceSession.Kind.DIRECT,
                    )
                    .first()
                )

            else:
                session = None

            if session is None:
                raise VoiceSessionNotFound

            participation = cls._require_active_participation(
                session=session,
                current_user=current_user,
                client_instance_id=client_instance_id,
            )

            return LiveKitMediaService.issue_join_credentials(
                room_name=session.media_room_name,
                participant_identity=participation.media_participant_identity,
            )
