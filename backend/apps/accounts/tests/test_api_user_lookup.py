from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase


User = get_user_model()


class UserLookupApiTests(APITestCase):

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
        self.bobby = User.objects.create_user(
            email="bobby@example.com",
            username="bobby",
            password="Strong-Test-Password!123",
        )

    def test_authenticated_user_can_search_by_username(self):
        self.client.force_login(self.alice)

        response = self.client.get(
            reverse("api-user-lookup"),
            {
                "search": "bob",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        results = response.data["results"]

        self.assertEqual(
            [item["username"] for item in results],
            [
                "bob",
                "bobby",
            ],
        )

    def test_lookup_does_not_expose_email(self):
        self.client.force_login(self.alice)

        response = self.client.get(
            reverse("api-user-lookup"),
            {
                "search": "bob",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertNotIn(
            "email",
            response.data["results"][0],
        )

    def test_lookup_excludes_current_user(self):
        self.client.force_login(self.alice)

        response = self.client.get(
            reverse("api-user-lookup"),
            {
                "search": "alice",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["results"],
            [],
        )

    def test_empty_search_returns_no_results(self):
        self.client.force_login(self.alice)

        response = self.client.get(
            reverse("api-user-lookup"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["results"],
            [],
        )

    def test_anonymous_user_gets_401(self):
        response = self.client.get(
            reverse("api-user-lookup"),
            {
                "search": "bob",
            },
        )

        self.assertEqual(
            response.status_code,
            401,
        )
