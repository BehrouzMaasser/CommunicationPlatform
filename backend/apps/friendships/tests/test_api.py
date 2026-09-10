from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.friendships.models import (
    FriendRequest,
    Friendship,
)
from apps.friendships.services import (
    FriendRequestService,
    FriendshipService,
)


User = get_user_model()


class FriendshipsApiTestBase(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.sam = User.objects.create_user(
            email="sam@example.com",
            username="sam",
            password=self.PASSWORD,
        )

        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password=self.PASSWORD,
        )

        self.dean = User.objects.create_user(
            email="dean@example.com",
            username="dean",
            password=self.PASSWORD,
        )

    def login(self, user):
        logged_in = self.client.login(
            email=user.email,
            password=self.PASSWORD,
        )

        self.assertTrue(logged_in)


class FriendshipsApiAuthenticationTests(
    FriendshipsApiTestBase
):

    def test_friendships_endpoints_require_authentication(self):
        endpoints = [
            (
                "get",
                reverse("friend-request-incoming-list"),
                None,
            ),
            (
                "get",
                reverse("friend-request-outgoing-list"),
                None,
            ),
            (
                "get",
                reverse("friend-list"),
                None,
            ),
            (
                "post",
                reverse("friend-request-create"),
                {"user_id": self.bob.pk},
            ),
            (
                "post",
                reverse(
                    "friend-request-accept",
                    kwargs={"request_id": 999},
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "friend-request-reject",
                    kwargs={"request_id": 999},
                ),
                None,
            ),
            (
                "delete",
                reverse(
                    "friend-request-cancel",
                    kwargs={"request_id": 999},
                ),
                None,
            ),
            (
                "delete",
                reverse(
                    "friendship-delete",
                    kwargs={"user_id": self.bob.pk},
                ),
                None,
            ),
        ]

        for method, url, data in endpoints:
            with self.subTest(
                method=method,
                url=url,
            ):
                response = getattr(
                    self.client,
                    method,
                )(
                    url,
                    data=data,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    401,
                )


class FriendRequestApiTests(
    FriendshipsApiTestBase
):

    # ------------------------------------------------------------
    # Create
    # ------------------------------------------------------------

    def test_create_friend_request(self):
        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            FriendRequest.objects.count(),
            1,
        )

        friend_request = FriendRequest.objects.get()

        self.assertEqual(
            friend_request.sender,
            self.sam,
        )

        self.assertEqual(
            friend_request.recipient,
            self.bob,
        )

    def test_create_friend_request_returns_public_user_data(self):
        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.data["sender"]["username"],
            "sam",
        )

        self.assertEqual(
            response.data["recipient"]["username"],
            "bob",
        )

        self.assertNotIn(
            "email",
            response.data["sender"],
        )

        self.assertNotIn(
            "email",
            response.data["recipient"],
        )

    def test_create_friend_request_to_unknown_user_returns_404(self):
        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": 999999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_create_self_friend_request_returns_400(self):
        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.sam.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_duplicate_pending_request_returns_409(self):
        FriendRequestService.send_friend_request(
            current_user=self.sam,
            target_user_id=self.bob.pk,
        )

        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_reverse_pending_request_returns_409(self):
        FriendRequestService.send_friend_request(
            current_user=self.sam,
            target_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.sam.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_friend_request_between_existing_friends_returns_409(self):
        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.bob,
        )

        self.login(self.sam)

        response = self.client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    # ------------------------------------------------------------
    # Incoming / outgoing
    # ------------------------------------------------------------

    def test_incoming_friend_requests_are_paginated(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.bob)

        response = self.client.get(
            reverse("friend-request-incoming-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "results",
            response.data,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            friend_request.pk,
        )

    def test_incoming_list_does_not_include_outgoing_requests(self):
        FriendRequestService.send_friend_request(
            current_user=self.sam,
            target_user_id=self.bob.pk,
        )

        FriendRequestService.send_friend_request(
            current_user=self.bob,
            target_user_id=self.dean.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse("friend-request-incoming-list")
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["sender"]["id"],
            self.sam.pk,
        )

    def test_outgoing_friend_requests_are_paginated(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.sam)

        response = self.client.get(
            reverse("friend-request-outgoing-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            friend_request.pk,
        )

    # ------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------

    def test_recipient_can_accept_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "friend-request-accept",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

        self.assertEqual(
            Friendship.objects.count(),
            1,
        )

        self.assertEqual(
            response.data["friend"]["id"],
            self.sam.pk,
        )

        self.assertNotIn(
            "email",
            response.data["friend"],
        )

    def test_sender_cannot_accept_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.sam)

        response = self.client.post(
            reverse(
                "friend-request-accept",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_accept_unknown_friend_request_returns_404(self):
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "friend-request-accept",
                kwargs={"request_id": 999999},
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    # ------------------------------------------------------------
    # Reject
    # ------------------------------------------------------------

    def test_recipient_can_reject_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "friend-request-reject",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

    def test_sender_cannot_reject_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.sam)

        response = self.client.post(
            reverse(
                "friend-request-reject",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------

    def test_sender_can_cancel_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.sam)

        response = self.client.delete(
            reverse(
                "friend-request-cancel",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )

    def test_recipient_cannot_cancel_friend_request(self):
        friend_request = (
            FriendRequestService.send_friend_request(
                current_user=self.sam,
                target_user_id=self.bob.pk,
            )
        )

        self.login(self.bob)

        response = self.client.delete(
            reverse(
                "friend-request-cancel",
                kwargs={
                    "request_id": friend_request.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            FriendRequest.objects.filter(
                pk=friend_request.pk,
            ).exists()
        )


class FriendApiTests(
    FriendshipsApiTestBase
):

    def test_friend_list_is_paginated(self):
        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.bob,
        )

        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.dean,
        )

        self.login(self.sam)

        response = self.client.get(
            reverse("friend-list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        self.assertIn(
            "results",
            response.data,
        )

    def test_friend_list_returns_public_user_representation(self):
        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.bob,
        )

        self.login(self.sam)

        response = self.client.get(
            reverse("friend-list")
        )

        friend = response.data["results"][0]

        self.assertEqual(
            friend["id"],
            self.bob.pk,
        )

        self.assertEqual(
            friend["username"],
            "bob",
        )

        self.assertNotIn(
            "email",
            friend,
        )

    def test_user_can_remove_friendship(self):
        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.bob,
        )

        self.login(self.sam)

        response = self.client.delete(
            reverse(
                "friendship-delete",
                kwargs={
                    "user_id": self.bob.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_either_participant_can_remove_friendship(self):
        FriendshipService._create_friendship(
            user_a=self.sam,
            user_b=self.bob,
        )

        self.login(self.bob)

        response = self.client.delete(
            reverse(
                "friendship-delete",
                kwargs={
                    "user_id": self.sam.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Friendship.objects.exists()
        )

    def test_removing_nonexistent_friendship_returns_404(self):
        self.login(self.sam)

        response = self.client.delete(
            reverse(
                "friendship-delete",
                kwargs={
                    "user_id": self.bob.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class FriendshipsApiCsrfTests(
    FriendshipsApiTestBase
):

    def setUp(self):
        super().setUp()

        self.csrf_client = APIClient(
            enforce_csrf_checks=True,
        )

        logged_in = self.csrf_client.login(
            email=self.sam.email,
            password=self.PASSWORD,
        )

        self.assertTrue(logged_in)

    def test_authenticated_unsafe_request_without_csrf_is_rejected(self):
        response = self.csrf_client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            FriendRequest.objects.exists()
        )

    def test_authenticated_unsafe_request_with_csrf_is_allowed(self):
        # GET a Django-rendered page containing {% csrf_token %}
        # so Django issues the csrftoken cookie.
        page_response = self.csrf_client.get(
            reverse("users-me")
        )

        self.assertEqual(
            page_response.status_code,
            200,
        )

        csrf_token = (
            self.csrf_client
            .cookies["csrftoken"]
            .value
        )

        response = self.csrf_client.post(
            reverse("friend-request-create"),
            {
                "user_id": self.bob.pk,
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(
            response.status_code,
            201,
        )
