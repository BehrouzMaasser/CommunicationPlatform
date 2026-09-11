from django.urls import path

from apps.accounts.api.v1.views import (
    CurrentUserAPIView,
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
]
