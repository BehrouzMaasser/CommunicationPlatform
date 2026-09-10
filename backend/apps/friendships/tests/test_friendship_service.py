from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.friendships.exceptions import (
    FriendshipNotFound,
    SelfFriendshipNotAllowed,
    UsersAlreadyFriends,
)
from apps.friendships.models import Friendship
from apps.friendships.services.friendship import FriendshipService


User = get_user_model()


class FriendshipServiceTests(TestCase):

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

    def test_create_friendship_stores_canonical_pair(self):
        friendship = FriendshipService._create_friendship(
            user_a=self.bob,
            user_b=self.alice,
        )

        self.assertEqual(
            friendship.user_1_id,
            min(self.alice.pk, self.bob.pk),
        )

        self.assertEqual(
            friendship.user_2_id,
            max(self.alice.pk, self.bob.pk),
        )

    def test_create_friendship_rejects_self_friendship(self):
        with self.assertRaises(SelfFriendshipNotAllowed):
            FriendshipService._create_friendship(
                user_a=self.alice,
                user_b=self.alice,
            )

        self.assertEqual(
            Friendship.objects.count(),
            0,
        )

    def test_create_friendship_rejects_existing_friendship(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        with self.assertRaises(UsersAlreadyFriends):
            FriendshipService._create_friendship(
                user_a=self.bob,
                user_b=self.alice,
            )

        self.assertEqual(
            Friendship.objects.count(),
            1,
        )

    def test_remove_friendship(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_remove_friendship_works_for_either_participant(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        FriendshipService.remove_friendship(
            current_user=self.bob,
            friend_user_id=self.alice.pk,
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_remove_nonexistent_friendship_raises(self):
        with self.assertRaises(FriendshipNotFound):
            FriendshipService.remove_friendship(
                current_user=self.alice,
                friend_user_id=self.bob.pk,
            )

    def test_remove_friendship_with_self_raises_not_found(self):
        with self.assertRaises(FriendshipNotFound):
            FriendshipService.remove_friendship(
                current_user=self.alice,
                friend_user_id=self.alice.pk,
            )
