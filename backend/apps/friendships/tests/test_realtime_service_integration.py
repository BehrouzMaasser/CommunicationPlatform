from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.friendships.models import FriendRequest, Friendship


User = get_user_model()


class FriendshipRealtimeServiceIntegrationTests(APITestCase):
    """
    Exercise:
        HTTP -> actual friendship service -> actual FriendshipRealtimePublisher

    Mock only the lower transport boundary.

    This is important because patching FriendshipRealtimePublisher itself would
    hide argument/signature mistakes such as forgetting friendship_id when
    publishing friend_request.accepted.
    """

    PUBLISH_PATH = (
        "apps.friendships.realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password-123",
        )

    def login(self, user):
        self.client.force_authenticate(user=user)

    @patch(PUBLISH_PATH)
    def test_send_reaches_real_realtime_adapter(self, publish):
        self.login(self.alice)

        response = self.client.post(
            "/api/v1/friend-requests/",
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        publish.assert_called_once()

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.created",
        )
        self.assertEqual(
            set(kwargs["user_ids"]),
            {self.alice.pk, self.bob.pk},
        )

    @patch(PUBLISH_PATH)
    def test_accept_reaches_real_adapter_with_friendship_id(self, publish):
        friend_request = FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        self.login(self.bob)

        response = self.client.post(
            f"/api/v1/friend-requests/{friend_request.pk}/accept/",
            {},
            format="json",
        )

        self.assertIn(response.status_code, {200, 201, 204})
        publish.assert_called_once()

        kwargs = publish.call_args.kwargs
        payload = kwargs["payload"]

        self.assertEqual(
            kwargs["event_type"].value,
            "friend_request.accepted",
        )
        self.assertIn(
            "friendship_id",
            payload,
        )

        self.assertTrue(
            Friendship.objects.filter(
                pk=payload["friendship_id"],
            ).exists()
        )

    @patch(PUBLISH_PATH)
    def test_reject_reaches_real_realtime_adapter(self, publish):
        friend_request = FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        self.login(self.bob)

        response = self.client.post(
            f"/api/v1/friend-requests/{friend_request.pk}/reject/",
            {},
            format="json",
        )

        self.assertIn(response.status_code, {200, 204})
        publish.assert_called_once()

        self.assertEqual(
            publish.call_args.kwargs["event_type"].value,
            "friend_request.rejected",
        )

    @patch(PUBLISH_PATH)
    def test_cancel_reaches_real_realtime_adapter(self, publish):
        friend_request = FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        self.login(self.alice)

        response = self.client.delete(
            f"/api/v1/friend-requests/{friend_request.pk}/"
        )

        self.assertEqual(response.status_code, 204)
        publish.assert_called_once()

        self.assertEqual(
            publish.call_args.kwargs["event_type"].value,
            "friend_request.cancelled",
        )

    @patch(PUBLISH_PATH)
    def test_unfriend_reaches_real_realtime_adapter(self, publish):
        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )

        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.login(self.alice)

        response = self.client.delete(
            f"/api/v1/friends/{self.bob.pk}/"
        )

        self.assertEqual(response.status_code, 204)
        publish.assert_called_once()

        self.assertEqual(
            publish.call_args.kwargs["event_type"].value,
            "friendship.removed",
        )
