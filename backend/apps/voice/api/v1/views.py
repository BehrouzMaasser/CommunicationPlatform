from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.selectors import GroupConversationSelector
from apps.voice.api.v1.exceptions import voice_error_response
from apps.voice.api.v1.serializers import (
    ClientInstanceSerializer,
    CurrentVoiceParticipationSerializer,
    DirectCallStartSerializer,
    VoiceMediaCredentialsSerializer,
    VoiceParticipationSerializer,
    VoiceSessionSerializer,
)
from apps.voice.exceptions import VoiceError, VoiceUnavailable
from apps.voice.selectors.voice_session import VoiceSessionSelector
from apps.voice.services.media_access import VoiceMediaAccessService
from apps.voice.services.voice_session import VoiceSessionService


def _require_voice_enabled() -> None:
    if not settings.VOICE_ENABLED:
        raise VoiceUnavailable("Voice communication is disabled.")


def _voice_state_data(*, session, current_user) -> dict:
    if session is None:
        return {
            "session": None,
            "current_participation": None,
            "participants": [],
        }

    participations = list(
        VoiceSessionSelector.list_open_participations_for_session(
            session=session,
        )
    )
    current_participation = next(
        (
            participation
            for participation in participations
            if participation.user_id == current_user.pk
        ),
        None,
    )

    return {
        "session": VoiceSessionSerializer(session).data,
        "current_participation": (
            CurrentVoiceParticipationSerializer(
                current_participation
            ).data
            if current_participation is not None
            else None
        ),
        "participants": VoiceParticipationSerializer(
            participations,
            many=True,
        ).data,
    }


def _handle_voice_operation(operation):
    try:
        _require_voice_enabled()
        return operation()
    except VoiceError as exc:
        return voice_error_response(exc)


class VoiceStateView(APIView):
    def get(self, request):
        def operation():
            participation = VoiceSessionService.reconcile_for_user(
                current_user=request.user,
            )
            session = (
                participation.session
                if participation is not None
                else None
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class DirectCallStartView(APIView):
    def post(self, request):
        serializer = DirectCallStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            session = VoiceSessionService.start_direct_call(
                current_user=request.user,
                target_user_id=serializer.validated_data["user_id"],
                client_instance_id=serializer.validated_data[
                    "client_instance_id"
                ],
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                ),
                status=status.HTTP_201_CREATED,
            )

        return _handle_voice_operation(operation)


class DirectCallAcceptView(APIView):
    def post(self, request, session_id):
        serializer = ClientInstanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            session = VoiceSessionService.accept_direct_call(
                current_user=request.user,
                session_id=session_id,
                client_instance_id=serializer.validated_data[
                    "client_instance_id"
                ],
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class DirectCallRejectView(APIView):
    def post(self, request, session_id):
        def operation():
            session = VoiceSessionService.reject_direct_call(
                current_user=request.user,
                session_id=session_id,
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class DirectCallCancelView(APIView):
    def post(self, request, session_id):
        def operation():
            session = VoiceSessionService.cancel_direct_call(
                current_user=request.user,
                session_id=session_id,
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class DirectCallEndView(APIView):
    def post(self, request, session_id):
        def operation():
            session = VoiceSessionService.end_direct_call(
                current_user=request.user,
                session_id=session_id,
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class GroupVoiceView(APIView):
    @staticmethod
    def _get_group_or_404(*, user, group_id):
        group = GroupConversationSelector.get_for_member(
            user=user,
            group_id=group_id,
        )
        if group is None:
            raise NotFound
        return group

    def get(self, request, group_id):
        def operation():
            self._get_group_or_404(
                user=request.user,
                group_id=group_id,
            )
            session = VoiceSessionSelector.get_active_group_session(
                group_id=group_id,
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)

    def post(self, request, group_id):
        serializer = ClientInstanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            self._get_group_or_404(
                user=request.user,
                group_id=group_id,
            )
            participation = VoiceSessionService.join_group_voice(
                current_user=request.user,
                group_id=group_id,
                client_instance_id=serializer.validated_data[
                    "client_instance_id"
                ],
            )
            return Response(
                _voice_state_data(
                    session=participation.session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class GroupVoiceLeaveView(APIView):
    def post(self, request, group_id):
        serializer = ClientInstanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            group = GroupConversationSelector.get_for_member(
                user=request.user,
                group_id=group_id,
            )
            if group is None:
                raise NotFound

            session = VoiceSessionService.leave_group_voice(
                current_user=request.user,
                group_id=group_id,
                client_instance_id=serializer.validated_data[
                    "client_instance_id"
                ],
            )
            return Response(
                _voice_state_data(
                    session=session,
                    current_user=request.user,
                )
            )

        return _handle_voice_operation(operation)


class VoiceMediaCredentialsView(APIView):
    def post(self, request, session_id):
        serializer = ClientInstanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            credentials = VoiceMediaAccessService.issue_credentials(
                current_user=request.user,
                session_id=session_id,
                client_instance_id=serializer.validated_data[
                    "client_instance_id"
                ],
            )
            output = VoiceMediaCredentialsSerializer(credentials)
            return Response(output.data)

        return _handle_voice_operation(operation)
