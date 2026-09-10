from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.friendships.models import (
    FriendRequest,
    Friendship,
)


User = get_user_model()


class FriendRequestModelConstraintTests(TestCase):

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

    def test_self_friend_request_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FriendRequest.objects.create(
                    sender=self.alice,
                    recipient=self.alice,
                )

        self.assertEqual(
            FriendRequest.objects.count(),
            0,
        )

    def test_duplicate_pending_request_is_rejected_by_database(self):
        FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FriendRequest.objects.create(
                    sender=self.alice,
                    recipient=self.bob,
                )

        self.assertEqual(
            FriendRequest.objects.count(),
            1,
        )

    def test_reverse_pending_request_is_rejected_by_database(self):
        FriendRequest.objects.create(
            sender=self.alice,
            recipient=self.bob,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FriendRequest.objects.create(
                    sender=self.bob,
                    recipient=self.alice,
                )

        self.assertEqual(
            FriendRequest.objects.count(),
            1,
        )


class FriendshipModelConstraintTests(TestCase):

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

    def test_self_friendship_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    user_1=self.alice,
                    user_2=self.alice,
                )

        self.assertEqual(
            Friendship.objects.count(),
            0,
        )

    def test_non_canonical_friendship_is_rejected_by_database(self):
        lower_id_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_id_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    user_1=higher_id_user,
                    user_2=lower_id_user,
                )

        self.assertEqual(
            Friendship.objects.count(),
            0,
        )

    def test_canonical_friendship_is_allowed_by_database(self):
        lower_id_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_id_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        friendship = Friendship.objects.create(
            user_1=lower_id_user,
            user_2=higher_id_user,
        )

        self.assertEqual(
            friendship.user_1,
            lower_id_user,
        )

        self.assertEqual(
            friendship.user_2,
            higher_id_user,
        )

    def test_duplicate_friendship_is_rejected_by_database(self):
        lower_id_user = min(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        higher_id_user = max(
            (self.alice, self.bob),
            key=lambda user: user.pk,
        )

        Friendship.objects.create(
            user_1=lower_id_user,
            user_2=higher_id_user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(
                    user_1=lower_id_user,
                    user_2=higher_id_user,
                )

        self.assertEqual(
            Friendship.objects.count(),
            1,
        )
