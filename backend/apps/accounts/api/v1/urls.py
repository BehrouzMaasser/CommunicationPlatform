from django.urls import path

from apps.accounts.api.v1.views import (
    CurrentUserAPIView,
    CurrentUserAvatarAPIView,
    UserAvatarAPIView,
    UserLookupAPIView,
)


urlpatterns = [
    path(
        "users/",
        UserLookupAPIView.as_view(),
        name="api-user-lookup",
    ),
    path(
        "users/me/",
        CurrentUserAPIView.as_view(),
        name="api-current-user",
    ),
    path(
        "users/me/avatar/",
        CurrentUserAvatarAPIView.as_view(),
        name="api-current-user-avatar",
    ),
    path(
        "users/<int:user_id>/avatar/",
        UserAvatarAPIView.as_view(),
        name="api-user-avatar",
    ),
]
