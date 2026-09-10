from django.urls import path

from apps.friendships.api.v1.views import (
    FriendListView,
    FriendRequestAcceptView,
    FriendRequestCancelView,
    FriendRequestCreateView,
    FriendRequestRejectView,
    FriendshipDeleteView,
    IncomingFriendRequestListView,
    OutgoingFriendRequestListView,
)


urlpatterns = [
    path(
        "friend-requests/",
        FriendRequestCreateView.as_view(),
        name="friend-request-create",
    ),
    path(
        "friend-requests/incoming/",
        IncomingFriendRequestListView.as_view(),
        name="friend-request-incoming-list",
    ),
    path(
        "friend-requests/outgoing/",
        OutgoingFriendRequestListView.as_view(),
        name="friend-request-outgoing-list",
    ),
    path(
        "friend-requests/<int:request_id>/accept/",
        FriendRequestAcceptView.as_view(),
        name="friend-request-accept",
    ),
    path(
        "friend-requests/<int:request_id>/reject/",
        FriendRequestRejectView.as_view(),
        name="friend-request-reject",
    ),
    path(
        "friend-requests/<int:request_id>/",
        FriendRequestCancelView.as_view(),
        name="friend-request-cancel",
    ),
    path(
        "friends/",
        FriendListView.as_view(),
        name="friend-list",
    ),
    path(
        "friends/<int:user_id>/",
        FriendshipDeleteView.as_view(),
        name="friendship-delete",
    ),
]