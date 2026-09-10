from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.friendships.api.v1.exceptions import (
    friendships_error_response,
)
from apps.friendships.api.v1.serializers import (
    FriendRequestSerializer,
    FriendshipSerializer,
    PublicUserSerializer,
    SendFriendRequestSerializer,
)
from apps.friendships.exceptions import FriendshipsError
from apps.friendships.selectors import (
    FriendRequestSelector,
    FriendshipSelector,
)
from apps.friendships.services import (
    FriendRequestService,
    FriendshipService,
)


class FriendRequestCreateView(APIView):

    def post(self, request):
        serializer = SendFriendRequestSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        try:
            friend_request = (
                FriendRequestService.send_friend_request(
                    current_user=request.user,
                    target_user_id=serializer.validated_data[
                        "user_id"
                    ],
                )
            )
        except FriendshipsError as exc:
            return friendships_error_response(exc)

        output_serializer = FriendRequestSerializer(
            friend_request
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class IncomingFriendRequestListView(generics.ListAPIView):
    serializer_class = FriendRequestSerializer

    def get_queryset(self):
        return FriendRequestSelector.list_incoming(
            user=self.request.user,
        )


class OutgoingFriendRequestListView(generics.ListAPIView):
    serializer_class = FriendRequestSerializer

    def get_queryset(self):
        return FriendRequestSelector.list_outgoing(
            user=self.request.user,
        )


class FriendRequestAcceptView(APIView):

    def post(self, request, request_id):
        try:
            friendship = (
                FriendRequestService.accept_friend_request(
                    current_user=request.user,
                    friend_request_id=request_id,
                )
            )
        except FriendshipsError as exc:
            return friendships_error_response(exc)

        serializer = FriendshipSerializer(
            friendship,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class FriendRequestRejectView(APIView):

    def post(self, request, request_id):
        try:
            FriendRequestService.reject_friend_request(
                current_user=request.user,
                friend_request_id=request_id,
            )
        except FriendshipsError as exc:
            return friendships_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class FriendRequestCancelView(APIView):

    def delete(self, request, request_id):
        try:
            FriendRequestService.cancel_pending_friend_request(
                current_user=request.user,
                friend_request_id=request_id,
            )
        except FriendshipsError as exc:
            return friendships_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class FriendListView(generics.ListAPIView):
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        return FriendshipSelector.list_friend_users(
            user=self.request.user,
        )


class FriendshipDeleteView(APIView):

    def delete(self, request, user_id):
        try:
            FriendshipService.remove_friendship(
                current_user=request.user,
                friend_user_id=user_id,
            )
        except FriendshipsError as exc:
            return friendships_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
