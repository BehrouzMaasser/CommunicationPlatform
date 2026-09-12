from unittest.mock import patch

from django.test import TestCase

from apps.friendships.realtime import (
    FriendshipRealtimePublisher,
)


class FriendshipRealtimePublisherTests(
    TestCase
):

    @patch(
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_request_created_targets_both_users(
        self,
        publish,
    ):
        (
            FriendshipRealtimePublisher
            .friend_request_created_after_commit(
                request_id=10,
                sender_id=1,
                sender_username="alice",
                recipient_id=2,
                recipient_username="bob",
            )
        )

        kwargs = (
            publish.call_args.kwargs
        )

        self.assertEqual(
            set(kwargs["user_ids"]),
            {1, 2},
        )
        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.created",
        )
        self.assertEqual(
            kwargs["payload"][
                "request_id"
            ],
            10,
        )

    @patch(
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_request_accepted_contains_friendship_id(
        self,
        publish,
    ):
        (
            FriendshipRealtimePublisher
            .friend_request_accepted_after_commit(
                request_id=10,
                sender_id=1,
                sender_username="alice",
                recipient_id=2,
                recipient_username="bob",
                friendship_id=99,
            )
        )

        kwargs = (
            publish.call_args.kwargs
        )

        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.accepted",
        )
        self.assertEqual(
            kwargs["payload"][
                "friendship_id"
            ],
            99,
        )

    @patch(
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_request_rejected_targets_both_users(
        self,
        publish,
    ):
        (
            FriendshipRealtimePublisher
            .friend_request_rejected_after_commit(
                request_id=10,
                sender_id=1,
                sender_username="alice",
                recipient_id=2,
                recipient_username="bob",
            )
        )

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.rejected",
        )
        self.assertEqual(
            set(kwargs["user_ids"]),
            {1, 2},
        )

    @patch(
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_request_cancelled_targets_both_users(
        self,
        publish,
    ):
        (
            FriendshipRealtimePublisher
            .friend_request_cancelled_after_commit(
                request_id=10,
                sender_id=1,
                sender_username="alice",
                recipient_id=2,
                recipient_username="bob",
            )
        )

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.cancelled",
        )

    @patch(
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_friendship_removed_targets_both_users(
        self,
        publish,
    ):
        (
            FriendshipRealtimePublisher
            .friendship_removed_after_commit(
                user_a_id=1,
                user_a_username="alice",
                user_b_id=2,
                user_b_username="bob",
            )
        )

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["event_type"].value,
            "friendship.removed",
        )
        self.assertEqual(
            set(kwargs["user_ids"]),
            {1, 2},
        )
