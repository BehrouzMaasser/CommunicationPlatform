from django.urls import path

from apps.conversations.api.v1.views import (
    DirectConversationDetailView,
    DirectConversationListCreateView,
    GroupConversationAvatarView,
    GroupConversationDetailView,
    GroupConversationLeaveView,
    GroupConversationListCreateView,
    GroupConversationRenameView,
    GroupInvitationAcceptView,
    GroupInvitationCancelView,
    GroupInvitationCreateView,
    GroupInvitationLinkCreateView,
    GroupInvitationLinkJoinView,
    GroupInvitationLinkRevokeView,
    GroupInvitationListView,
    GroupInvitationRejectView,
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
        "groups/<int:group_id>/avatar/",
        GroupConversationAvatarView.as_view(),
        name="api-group-avatar",
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

    # Direct group invitations
    path(
        "groups/<int:group_id>/invitations/",
        GroupInvitationCreateView.as_view(),
        name="group-invitation-create",
    ),
    path(
        "groups/<int:group_id>/invitations/<int:invitation_id>/",
        GroupInvitationCancelView.as_view(),
        name="group-invitation-cancel",
    ),
    path(
        "group-invitations/",
        GroupInvitationListView.as_view(),
        name="group-invitation-list",
    ),
    path(
        "group-invitations/<int:invitation_id>/accept/",
        GroupInvitationAcceptView.as_view(),
        name="group-invitation-accept",
    ),
    path(
        "group-invitations/<int:invitation_id>/reject/",
        GroupInvitationRejectView.as_view(),
        name="group-invitation-reject",
    ),

    # Invitation links
    path(
        "groups/<int:group_id>/invitation-links/",
        GroupInvitationLinkCreateView.as_view(),
        name="group-invitation-link-create",
    ),
    path(
        "groups/<int:group_id>/invitation-links/<int:link_id>/",
        GroupInvitationLinkRevokeView.as_view(),
        name="group-invitation-link-revoke",
    ),
    path(
        "group-invitations/<str:token>/join/",
        GroupInvitationLinkJoinView.as_view(),
        name="group-invitation-link-join",
    ),
]
