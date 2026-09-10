from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.friendships.exceptions import (
    FriendRequestAlreadyPending,
    FriendRequestNotFound,
    FriendRequestRecipientRequired,
    FriendRequestSenderRequired,
    SelfFriendRequestNotAllowed,
    TargetUserNotFound,
    UsersAlreadyFriends,
)
from apps.friendships.models import (
    FriendRequest,
    Friendship,
)
from apps.friendships.services.friend_request import (
    FriendRequestService,
)
from apps.friendships.services.friendship import (
    FriendshipService,
)


User = get_user_model()


class FriendRequestServiceTests(TestCase):

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

    # ---------------------------------------------------------------
    # Send
    # ---------------------------------------------------------------

    def test_send_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        self.assertEqual(
            friend_request.sender,
            self.alice,
        )

        self.assertEqual(
            friend_request.recipient,
            self.bob,
        )

        self.assertEqual(
            FriendRequest.objects.count(),
            1,
        )

    def test_send_friend_request_to_unknown_user_raises(self):
        with self.assertRaises(TargetUserNotFound):
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=999999,
            )

    def test_user_cannot_send_friend_request_to_self(self):
        with self.assertRaises(SelfFriendRequestNotAllowed):
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.alice.pk,
            )

    def test_cannot_send_request_when_users_are_already_friends(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        with self.assertRaises(UsersAlreadyFriends):
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )

    def test_cannot_send_duplicate_pending_request(self):
        FriendRequestService.send_friend_request(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        with self.assertRaises(FriendRequestAlreadyPending):
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )

    def test_cannot_send_reverse_pending_request(self):
        FriendRequestService.send_friend_request(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        with self.assertRaises(FriendRequestAlreadyPending):
            FriendRequestService.send_friend_request(
                current_user=self.bob,
                target_user_id=self.alice.pk,
            )

    # ---------------------------------------------------------------
    # Accept
    # ---------------------------------------------------------------

    def test_recipient_can_accept_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        friendship = (
            FriendRequestService.accept_friend_request(
                current_user=self.bob,
                friend_request_id=friend_request.pk,
            )
        )

        self.assertTrue(
            Friendship.objects.filter(
                pk=friendship.pk,
            ).exists()
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

        self.assertEqual(
            friendship.user_1_id,
            min(self.alice.pk, self.bob.pk),
        )

        self.assertEqual(
            friendship.user_2_id,
            max(self.alice.pk, self.bob.pk),
        )

    def test_sender_cannot_accept_own_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        with self.assertRaises(
            FriendRequestRecipientRequired
        ):
            FriendRequestService.accept_friend_request(
                current_user=self.alice,
                friend_request_id=friend_request.pk,
            )

        self.assertTrue(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_third_user_cannot_accept_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        with self.assertRaises(
            FriendRequestRecipientRequired
        ):
            FriendRequestService.accept_friend_request(
                current_user=self.charlie,
                friend_request_id=friend_request.pk,
            )

    def test_accept_unknown_request_raises(self):
        with self.assertRaises(FriendRequestNotFound):
            FriendRequestService.accept_friend_request(
                current_user=self.bob,
                friend_request_id=999999,
            )

    # ---------------------------------------------------------------
    # Reject
    # ---------------------------------------------------------------

    def test_recipient_can_reject_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        FriendRequestService.reject_friend_request(
            current_user=self.bob,
            friend_request_id=friend_request.pk,
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_sender_cannot_reject_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        with self.assertRaises(
            FriendRequestRecipientRequired
        ):
            FriendRequestService.reject_friend_request(
                current_user=self.alice,
                friend_request_id=friend_request.pk,
            )

        self.assertTrue(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

    # ---------------------------------------------------------------
    # Cancel
    # ---------------------------------------------------------------

    def test_sender_can_cancel_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        FriendRequestService.cancel_pending_friend_request(
            current_user=self.alice,
            friend_request_id=friend_request.pk,
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

    def test_recipient_cannot_cancel_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        with self.assertRaises(
            FriendRequestSenderRequired
        ):
            FriendRequestService.cancel_pending_friend_request(
                current_user=self.bob,
                friend_request_id=friend_request.pk,
            )

        self.assertTrue(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

    def test_third_user_cannot_cancel_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        with self.assertRaises(
            FriendRequestSenderRequired
        ):
            FriendRequestService.cancel_pending_friend_request(
                current_user=self.charlie,
                friend_request_id=friend_request.pk,
            )
