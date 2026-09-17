from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.serializers import (
    AvatarUploadSerializer,
    CurrentUserSerializer,
    PublicUserSerializer,
)
from apps.accounts.exceptions import InvalidAvatar
from apps.accounts.selectors import UserSelector
from apps.accounts.services.avatar import AvatarService


User = get_user_model()


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(
            request.user,
        )

        return Response(serializer.data)


class CurrentUserAvatarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = AvatarUploadSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        try:
            AvatarService.replace_avatar(
                user=request.user,
                file_obj=serializer.validated_data["avatar"],
            )
        except InvalidAvatar as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CurrentUserSerializer(
                request.user,
            ).data,
        )

    def delete(self, request):
        AvatarService.remove_avatar(
            user=request.user,
        )

        return Response(
            CurrentUserSerializer(
                request.user,
            ).data,
            status=status.HTTP_200_OK,
        )


class UserAvatarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        del request

        user = get_object_or_404(
            User.objects.only(
                "id",
                "avatar",
            ),
            pk=user_id,
        )

        if not user.avatar:
            raise Http404

        try:
            avatar_file = user.avatar.open("rb")
        except (FileNotFoundError, OSError) as exc:
            raise Http404 from exc

        response = FileResponse(
            avatar_file,
            content_type="image/webp",
        )
        response["Cache-Control"] = (
            "private, max-age=31536000, immutable"
        )
        return response


class UserLookupAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        return UserSelector.search_public_users(
            current_user=self.request.user,
            search=self.request.query_params.get(
                "search",
                "",
            ),
        )
