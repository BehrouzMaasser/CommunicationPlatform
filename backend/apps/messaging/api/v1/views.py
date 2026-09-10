from rest_framework import generics, mixins, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attachments.exceptions import AttachmentsError
from apps.attachments.services import (
    MessageAttachmentService,
)
from apps.conversations.selectors import (
    DirectConversationSelector,
    GroupConversationSelector,
)
from apps.messaging.api.v1.exceptions import (
    messaging_error_response,
)
from apps.messaging.api.v1.serializers import (
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.messaging.exceptions import MessagingError
from apps.messaging.selectors import MessageSelector


def _get_accessible_direct_conversation_or_404(
    *,
    user,
    conversation_id,
):
    conversation = DirectConversationSelector.get_for_user(
        user=user,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise NotFound

    return conversation


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


def _message_create_error_response(exc):
    if isinstance(exc, MessagingError):
        return messaging_error_response(exc)

    # Attachment validation errors are client payload errors.
    return Response(
        {
            "detail": exc.message,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


class DirectMessageListCreateView(
    mixins.ListModelMixin,
    generics.GenericAPIView,
):
    serializer_class = MessageSerializer

    def _get_conversation(self):
        return _get_accessible_direct_conversation_or_404(
            user=self.request.user,
            conversation_id=self.kwargs["conversation_id"],
        )

    def get_queryset(self):
        conversation = self._get_conversation()

        return MessageSelector.list_for_direct_conversation(
            conversation=conversation,
        )

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "request": self.request,
        }

    def get(self, request, conversation_id):
        return self.list(request)

    def post(self, request, conversation_id):
        # Preserve private-resource semantics before payload validation.
        self._get_conversation()

        input_serializer = MessageCreateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        files = request.FILES.getlist(
            "attachments"
        )

        try:
            message = (
                MessageAttachmentService
                .create_message_with_attachments(
                    current_user=request.user,
                    direct_conversation_id=conversation_id,
                    content=input_serializer.validated_data[
                        "content"
                    ],
                    files=files,
                    reply_to_id=(
                        input_serializer
                        .validated_data
                        .get("reply_to_id")
                    ),
                )
            )
        except (MessagingError, AttachmentsError) as exc:
            return _message_create_error_response(exc)

        output_serializer = MessageSerializer(
            message,
            context={
                "request": request,
            },
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class GroupMessageListCreateView(
    mixins.ListModelMixin,
    generics.GenericAPIView,
):
    serializer_class = MessageSerializer

    def _get_group(self):
        return _get_accessible_group_or_404(
            user=self.request.user,
            group_id=self.kwargs["group_id"],
        )

    def get_queryset(self):
        group = self._get_group()

        return MessageSelector.list_for_group(
            group=group,
        )

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "request": self.request,
        }

    def get(self, request, group_id):
        return self.list(request)

    def post(self, request, group_id):
        self._get_group()

        input_serializer = MessageCreateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(
            raise_exception=True,
        )

        files = request.FILES.getlist(
            "attachments"
        )

        try:
            message = (
                MessageAttachmentService
                .create_message_with_attachments(
                    current_user=request.user,
                    group_id=group_id,
                    content=input_serializer.validated_data[
                        "content"
                    ],
                    files=files,
                    reply_to_id=(
                        input_serializer
                        .validated_data
                        .get("reply_to_id")
                    ),
                )
            )
        except (MessagingError, AttachmentsError) as exc:
            return _message_create_error_response(exc)

        output_serializer = MessageSerializer(
            message,
            context={
                "request": request,
            },
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class MessageDetailView(APIView):

    def get(self, request, message_id):
        message = MessageSelector.get_for_user(
            user=request.user,
            message_id=message_id,
        )

        if message is None:
            raise NotFound

        serializer = MessageSerializer(
            message,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
