from django.urls import include, path


urlpatterns = [
    path(
        "",
        include("apps.activity.api.v1.urls"),
    ),
    path(
        "",
        include("apps.accounts.api.v1.urls"),
    ),
    path(
        "",
        include("apps.friendships.api.v1.urls"),
    ),
    path(
        "",
        include("apps.conversations.api.v1.urls"),
    ),
    path(
        "",
        include("apps.messaging.api.v1.urls"),
    ),
    path(
        "",
        include("apps.attachments.api.v1.urls"),
    ),
    path(
        "",
        include("apps.voice.api.v1.urls"),
    ),
]
