from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.serializers import (
    CurrentUserSerializer,
    PublicUserSerializer,
)
from apps.accounts.selectors import UserSelector


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(
            request.user,
        )

        return Response(serializer.data)


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
