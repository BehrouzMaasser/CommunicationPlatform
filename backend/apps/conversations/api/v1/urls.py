from django.urls import path

from apps.conversations.api.v1.views import (
    DirectConversationDetailView,
    DirectConversationListCreateView,
    GroupConversationDetailView,
    GroupConversationLeaveView,
    GroupConversationListCreateView,
    GroupConversationRenameView,
    GroupMemberDeleteView,
    GroupMemberListView,
)


urlpatterns = [
    # Direct conversations
    path(
        "dms/",
        DirectConversationListCreateView.as_view(),
        name="dm-list-create",
    ),
    path(
        "dms/<int:conversation_id>/",
        DirectConversationDetailView.as_view(),
        name="dm-detail",
    ),

    # Groups
    path(
        "groups/",
        GroupConversationListCreateView.as_view(),
        name="group-list-create",
    ),
    path(
        "groups/<int:group_id>/",
        GroupConversationDetailView.as_view(),
        name="group-detail",
    ),
    path(
        "groups/<int:group_id>/rename/",
        GroupConversationRenameView.as_view(),
        name="group-rename",
    ),
    path(
        "groups/<int:group_id>/leave/",
        GroupConversationLeaveView.as_view(),
        name="group-leave",
    ),
    path(
        "groups/<int:group_id>/members/",
        GroupMemberListView.as_view(),
        name="group-member-list",
    ),
    path(
        "groups/<int:group_id>/members/<int:user_id>/",
        GroupMemberDeleteView.as_view(),
        name="group-member-delete",
    ),
]
