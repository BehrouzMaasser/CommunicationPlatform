from django.urls import path

from apps.messaging.api.v1.views import (
    DirectMessageListCreateView,
    GroupMessageListCreateView,
    MessageDetailView,
)


urlpatterns = [
    path(
        "dms/<int:conversation_id>/messages/",
        DirectMessageListCreateView.as_view(),
        name="dm-message-list-create",
    ),
    path(
        "groups/<int:group_id>/messages/",
        GroupMessageListCreateView.as_view(),
        name="group-message-list-create",
    ),
    path(
        "messages/<int:message_id>/",
        MessageDetailView.as_view(),
        name="message-detail",
    ),
]
