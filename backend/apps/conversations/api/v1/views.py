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
    GroupMembershipSerializer,
    GroupNameSerializer,
)
from apps.conversations.exceptions import ConversationsError
from apps.conversations.selectors import (
    DirectConversationSelector,
    GroupConversationSelector,
)
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
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
        # Hide the existence of groups from non-members.
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
        # Outsiders should receive 404 rather than learning that
        # the group exists.
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
