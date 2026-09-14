from rest_framework import generics, mixins, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.api.v1.exceptions import (
    conversations_error_response,
)
from apps.conversations.api.v1.serializers import (
    DirectConversationCreateSerializer,
    DirectConversationSerializer,
    GroupConversationSerializer,
    GroupInvitationCreateSerializer,
    GroupInvitationLinkCreateResponseSerializer,
    GroupInvitationSerializer,
    GroupMembershipSerializer,
    GroupNameSerializer,
)
from apps.conversations.exceptions import (
    ConversationsError,
    GroupOwnerRequired,
)
from apps.conversations.selectors import (
    DirectConversationSelector,
    GroupConversationSelector,
    GroupInvitationSelector,
)
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
    GroupInvitationLinkService,
    GroupInvitationService,
)


def _get_accessible_group_or_404(
    *,
    user,
    group_id,
):
    group = GroupConversationSelector.get_for_member(
        user=user,
        group_id=group_id,
    )

    if group is None:
        raise NotFound

    return group


# ---------------------------------------------------------------------
# Direct conversations
# ---------------------------------------------------------------------


class DirectConversationListCreateView(
    mixins.ListModelMixin,
    generics.GenericAPIView,
):
    serializer_class = DirectConversationSerializer

    def get_queryset(self):
        return DirectConversationSelector.list_for_user(
            user=self.request.user,
        )

    def get(self, request):
        return self.list(
            request,
        )

    def post(self, request):
        input_serializer = (
            DirectConversationCreateSerializer(
                data=request.data,
            )
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        try:
            conversation, created = (
                DirectConversationService.get_or_create(
                    current_user=request.user,
                    target_user_id=(
                        input_serializer
                        .validated_data["user_id"]
                    ),
                )
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = DirectConversationSerializer(
            conversation,
            context={
                "request": request,
            },
        )

        return Response(
            output_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class DirectConversationDetailView(APIView):

    def get(self, request, conversation_id):
        conversation = (
            DirectConversationSelector.get_for_user(
                user=request.user,
                conversation_id=conversation_id,
            )
        )

        if conversation is None:
            raise NotFound

        serializer = DirectConversationSerializer(
            conversation,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------


class GroupConversationListCreateView(
    mixins.ListModelMixin,
    generics.GenericAPIView,
):
    serializer_class = GroupConversationSerializer

    def get_queryset(self):
        return GroupConversationSelector.list_for_user(
            user=self.request.user,
        )

    def get(self, request):
        return self.list(
            request,
        )

    def post(self, request):
        input_serializer = GroupNameSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        try:
            group = GroupConversationService.create_group(
                current_user=request.user,
                name=input_serializer.validated_data[
                    "name"
                ],
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = GroupConversationSerializer(
            group,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class GroupConversationDetailView(APIView):

    def get(self, request, group_id):
        group = _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        serializer = GroupConversationSerializer(
            group,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, group_id):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        try:
            GroupConversationService.disband_group(
                current_user=request.user,
                group_id=group_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class GroupConversationRenameView(APIView):

    def patch(self, request, group_id):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        input_serializer = GroupNameSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        try:
            group = GroupConversationService.rename_group(
                current_user=request.user,
                group_id=group_id,
                name=input_serializer.validated_data[
                    "name"
                ],
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = GroupConversationSerializer(
            group,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )


class GroupConversationLeaveView(APIView):

    def post(self, request, group_id):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        try:
            GroupConversationService.leave_group(
                current_user=request.user,
                group_id=group_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class GroupMemberListView(generics.ListAPIView):
    serializer_class = GroupMembershipSerializer

    def get_queryset(self):
        group = _get_accessible_group_or_404(
            user=self.request.user,
            group_id=self.kwargs["group_id"],
        )

        return GroupConversationSelector.list_members(
            group=group,
        )


class GroupMemberDeleteView(APIView):

    def delete(
        self,
        request,
        group_id,
        user_id,
    ):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        try:
            GroupConversationService.remove_member(
                current_user=request.user,
                group_id=group_id,
                member_user_id=user_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


# ---------------------------------------------------------------------
# Direct group invitations
# ---------------------------------------------------------------------


class GroupInvitationCreateView(APIView):

    def get(self, request, group_id):
        group = _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        is_owner = GroupConversationSelector.is_owner(
            group=group,
            user=request.user,
        )

        if not is_owner:
            return conversations_error_response(
                GroupOwnerRequired()
            )

        invitations = (
            GroupInvitationSelector
            .list_for_group(
                group_id=group_id,
            )
        )

        serializer = GroupInvitationSerializer(
            invitations,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, group_id):
        # Preserve private-group existence semantics:
        # outsider -> 404, member-but-not-owner -> service returns 403.
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        input_serializer = GroupInvitationCreateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        try:
            invitation = GroupInvitationService.create_invitation(
                current_user=request.user,
                group_id=group_id,
                target_user_id=(
                    input_serializer
                    .validated_data["user_id"]
                ),
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = GroupInvitationSerializer(
            invitation,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class GroupInvitationListView(generics.ListAPIView):
    serializer_class = GroupInvitationSerializer

    def get_queryset(self):
        return GroupInvitationSelector.list_incoming(
            user=self.request.user,
        )


class GroupInvitationAcceptView(APIView):

    def post(self, request, invitation_id):
        invitation = GroupInvitationSelector.get_for_recipient(
            user=request.user,
            invitation_id=invitation_id,
        )

        if invitation is None:
            raise NotFound

        try:
            membership = GroupInvitationService.accept_invitation(
                current_user=request.user,
                invitation_id=invitation_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = GroupMembershipSerializer(
            membership,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )


class GroupInvitationRejectView(APIView):

    def post(self, request, invitation_id):
        invitation = GroupInvitationSelector.get_for_recipient(
            user=request.user,
            invitation_id=invitation_id,
        )

        if invitation is None:
            raise NotFound

        try:
            GroupInvitationService.reject_invitation(
                current_user=request.user,
                invitation_id=invitation_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


# ---------------------------------------------------------------------
# Group invitation links
# ---------------------------------------------------------------------


class GroupInvitationLinkCreateView(APIView):

    def post(self, request, group_id):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        try:
            link, token = GroupInvitationLinkService.create_link(
                current_user=request.user,
                group_id=group_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = (
            GroupInvitationLinkCreateResponseSerializer(
                {
                    "id": link.pk,
                    "token": token,
                    "created_at": link.created_at,
                    "expires_at": link.expires_at,
                }
            )
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class GroupInvitationLinkJoinView(APIView):

    def post(self, request, token):
        try:
            membership, created = (
                GroupInvitationLinkService.join_with_token(
                    current_user=request.user,
                    token=token,
                )
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        output_serializer = GroupMembershipSerializer(
            membership,
        )

        return Response(
            output_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class GroupInvitationLinkRevokeView(APIView):

    def delete(
        self,
        request,
        group_id,
        link_id,
    ):
        _get_accessible_group_or_404(
            user=request.user,
            group_id=group_id,
        )

        try:
            GroupInvitationLinkService.revoke_link(
                current_user=request.user,
                group_id=group_id,
                link_id=link_id,
            )
        except ConversationsError as exc:
            return conversations_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
