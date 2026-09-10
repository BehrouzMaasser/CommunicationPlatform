from django.urls import include, path


urlpatterns = [
    path(
        "",
        include("apps.friendships.api.v1.urls"),
    ),
    path(
        "",
        include("apps.conversations.api.v1.urls"),
    )
]
