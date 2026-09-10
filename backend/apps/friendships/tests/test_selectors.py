from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.friendships.models import FriendRequest
from apps.friendships.selectors import (
    FriendRequestSelector,
    FriendshipSelector,
)
from apps.friendships.services.friendship import (
    FriendshipService,
)


User = get_user_model()


class FriendRequestSelectorTests(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )

        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password="Strong-Test-Password!123",
        )

        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password="Strong-Test-Password!123",
        )

    def test_list_incoming_requests(self):
        alice_to_bob = FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.charlie,
        )

        incoming = list(
            FriendRequestSelector.list_incoming(
                user=self.bob,
            )
        )

        self.assertEqual(
            incoming,
            [alice_to_bob],
        )

    def test_list_outgoing_requests(self):
        alice_to_bob = FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        FriendRequest.objects.create(
            sender=self.charlie,
            recipient=self.bob,
        )

        outgoing = list(
            FriendRequestSelector.list_outgoing(
                user=self.alice,
            )
        )

        self.assertEqual(
            outgoing,
            [alice_to_bob],
        )

    def test_pending_exists_between_users_in_either_direction(self):
        FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        self.assertTrue(
            FriendRequestSelector.pending_exists_between_users(
                user_a=self.alice,
                user_b=self.bob,
            )
        )

        self.assertTrue(
            FriendRequestSelector.pending_exists_between_users(
                user_a=self.bob,
                user_b=self.alice,
            )
        )

    def test_pending_does_not_exist_between_unrelated_users(self):
        self.assertFalse(
            FriendRequestSelector.pending_exists_between_users(
                user_a=self.alice,
                user_b=self.bob,
            )
        )


class FriendshipSelectorTests(TestCase):

    def setUp(self):
        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )

        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password="Strong-Test-Password!123",
        )

        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password="Strong-Test-Password!123",
        )

    def test_exists_between_users(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        self.assertTrue(
            FriendshipSelector.exists_between_users(
                user_a=self.alice,
                user_b=self.bob,
            )
        )

        self.assertTrue(
            FriendshipSelector.exists_between_users(
                user_a=self.bob,
                user_b=self.alice,
            )
        )

    def test_user_is_not_friends_with_self(self):
        self.assertFalse(
            FriendshipSelector.exists_between_users(
                user_a=self.alice,
                user_b=self.alice,
            )
        )

    def test_get_between_users(self):
        friendship = FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        result = FriendshipSelector.get_between_users(
            user_a=self.bob,
            user_b=self.alice,
        )

        self.assertEqual(
            result,
            friendship,
        )

    def test_get_between_users_returns_none_when_missing(self):
        result = FriendshipSelector.get_between_users(
            user_a=self.alice,
            user_b=self.bob,
        )

        self.assertIsNone(result)

    def test_list_for_user(self):
        alice_bob = FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        alice_charlie = FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.charlie,
        )

        friendships = list(
            FriendshipSelector.list_for_user(
                user=self.alice,
            )
        )

        self.assertEqual(
            set(friendships),
            {
                alice_bob,
                alice_charlie,
            },
        )

    def test_list_friend_users(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.charlie,
        )

        friends = list(
            FriendshipSelector.list_friend_users(
                user=self.alice,
            )
        )

        self.assertEqual(
            friends,
            [
                self.bob,
                self.charlie,
            ],
        )
