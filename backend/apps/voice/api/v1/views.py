from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, status
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
    VoiceRoomInvitationCreateSerializer,
    VoiceRoomInvitationSerializer,
    VoiceRoomMembershipSerializer,
    VoiceRoomNameSerializer,
    VoiceRoomSerializer,
    VoiceParticipationSerializer,
    VoiceSessionSerializer,
)
from apps.voice.exceptions import VoiceError, VoiceUnavailable
from apps.voice.selectors.voice_room import VoiceRoomSelector
from apps.voice.selectors.voice_room_invitation import (
    VoiceRoomInvitationSelector,
)
from apps.voice.selectors.voice_session import VoiceSessionSelector
from apps.voice.services.media_access import VoiceMediaAccessService
from apps.voice.services.voice_room import VoiceRoomService
from apps.voice.services.voice_room_invitation import (
    VoiceRoomInvitationService,
)
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


def _require_voice_enabled() -> None:
    if not settings.VOICE_ENABLED:
        raise VoiceUnavailable("Voice communication is disabled.")



def _get_voice_room_for_member_or_404(
    *,
    user,
    room_id,
):
    room = VoiceRoomSelector.get_for_member(
        user=user,
        room_id=room_id,
    )

    if room is None:
        raise NotFound

    return room


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


class VoiceRoomListCreateView(
    generics.ListAPIView
):
    serializer_class = VoiceRoomSerializer

    def get_queryset(self):
        return VoiceRoomSelector.list_for_user(
            user=self.request.user,
        )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        def operation():
            return self.list(
                request,
                *args,
                **kwargs,
            )

        return _handle_voice_operation(
            operation
        )

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = VoiceRoomNameSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True
        )

        def operation():
            room = VoiceRoomService.create_room(
                current_user=request.user,
                name=(
                    serializer
                    .validated_data["name"]
                ),
            )

            return Response(
                VoiceRoomSerializer(
                    room
                ).data,
                status=(
                    status.HTTP_201_CREATED
                ),
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomDetailView(APIView):

    def get(
        self,
        request,
        room_id,
    ):
        def operation():
            room = (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            return Response(
                VoiceRoomSerializer(
                    room
                ).data
            )

        return _handle_voice_operation(
            operation
        )

    def patch(
        self,
        request,
        room_id,
    ):
        serializer = VoiceRoomNameSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True
        )

        def operation():
            (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            room = VoiceRoomService.rename_room(
                current_user=request.user,
                room_id=room_id,
                name=(
                    serializer
                    .validated_data["name"]
                ),
            )

            return Response(
                VoiceRoomSerializer(
                    room
                ).data
            )

        return _handle_voice_operation(
            operation
        )

    def delete(
        self,
        request,
        room_id,
    ):
        def operation():
            (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            VoiceRoomService.delete_room(
                current_user=request.user,
                room_id=room_id,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomMemberListView(
    generics.ListAPIView
):
    serializer_class = (
        VoiceRoomMembershipSerializer
    )

    def get_queryset(self):
        room = (
            _get_voice_room_for_member_or_404(
                user=self.request.user,
                room_id=self.kwargs["room_id"],
            )
        )

        return VoiceRoomSelector.list_members(
            room=room,
        )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        def operation():
            return self.list(
                request,
                *args,
                **kwargs,
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomLeaveView(APIView):

    def delete(
        self,
        request,
        room_id,
    ):
        def operation():
            (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            VoiceRoomService.leave_room(
                current_user=request.user,
                room_id=room_id,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomMemberDeleteView(APIView):

    def delete(
        self,
        request,
        room_id,
        user_id,
    ):
        def operation():
            room = (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            # Check ownership before resolving
            # the target user so ordinary members
            # cannot probe arbitrary user ids.
            VoiceRoomService._require_owner(
                room=room,
                user=request.user,
            )

            target_user = (
                User.objects
                .filter(
                    pk=user_id,
                )
                .first()
            )

            if target_user is None:
                raise NotFound

            VoiceRoomService.remove_member(
                current_user=request.user,
                room_id=room_id,
                target_user=target_user,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomInvitationCollectionView(
    generics.ListAPIView
):
    serializer_class = VoiceRoomInvitationSerializer

    def _get_room_for_owner(self):
        room = (
            _get_voice_room_for_member_or_404(
                user=self.request.user,
                room_id=self.kwargs["room_id"],
            )
        )

        VoiceRoomService._require_owner(
            room=room,
            user=self.request.user,
        )

        return room

    def get_queryset(self):
        room = self._get_room_for_owner()

        return (
            VoiceRoomInvitationSelector
            .list_for_room(
                room=room,
            )
        )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        def operation():
            return self.list(
                request,
                *args,
                **kwargs,
            )

        return _handle_voice_operation(
            operation
        )

    def post(
        self,
        request,
        room_id,
    ):
        def operation():
            self._get_room_for_owner()

            serializer = (
                VoiceRoomInvitationCreateSerializer(
                    data=request.data,
                )
            )
            serializer.is_valid(
                raise_exception=True
            )

            invitation = (
                VoiceRoomInvitationService
                .create_invitation(
                    current_user=request.user,
                    room_id=room_id,
                    target_user_id=(
                        serializer
                        .validated_data["user_id"]
                    ),
                )
            )

            return Response(
                VoiceRoomInvitationSerializer(
                    invitation
                ).data,
                status=status.HTTP_201_CREATED,
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomInvitationCancelView(APIView):

    def delete(
        self,
        request,
        room_id,
        invitation_id,
    ):
        def operation():
            room = (
                _get_voice_room_for_member_or_404(
                    user=request.user,
                    room_id=room_id,
                )
            )

            VoiceRoomService._require_owner(
                room=room,
                user=request.user,
            )

            (
                VoiceRoomInvitationService
                .cancel_invitation(
                    current_user=request.user,
                    room_id=room_id,
                    invitation_id=invitation_id,
                )
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomIncomingInvitationListView(
    generics.ListAPIView
):
    serializer_class = VoiceRoomInvitationSerializer

    def get_queryset(self):
        return (
            VoiceRoomInvitationSelector
            .list_for_recipient(
                user=self.request.user,
            )
        )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        def operation():
            return self.list(
                request,
                *args,
                **kwargs,
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomInvitationAcceptView(APIView):

    def post(
        self,
        request,
        invitation_id,
    ):
        def operation():
            membership = (
                VoiceRoomInvitationService
                .accept_invitation(
                    current_user=request.user,
                    invitation_id=invitation_id,
                )
            )

            return Response(
                VoiceRoomMembershipSerializer(
                    membership
                ).data,
                status=status.HTTP_201_CREATED,
            )

        return _handle_voice_operation(
            operation
        )


class VoiceRoomInvitationRejectView(APIView):

    def post(
        self,
        request,
        invitation_id,
    ):
        def operation():
            (
                VoiceRoomInvitationService
                .reject_invitation(
                    current_user=request.user,
                    invitation_id=invitation_id,
                )
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        return _handle_voice_operation(
            operation
        )
