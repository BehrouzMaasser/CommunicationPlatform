from django.urls import include, path


urlpatterns = [
    path(
        "",
        include("apps.friendships.api.v1.urls"),
    ),
]
