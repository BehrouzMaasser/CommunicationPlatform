from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase


User = get_user_model()


class CurrentUserApiTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )

    def test_authenticated_user_can_get_current_user(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("api-current-user"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["id"],
            self.user.pk,
        )
        self.assertEqual(
            response.data["username"],
            "alice",
        )
        self.assertEqual(
            response.data["email"],
            "alice@example.com",
        )
        self.assertIsNone(
            response.data["avatar_url"],
        )

    def test_anonymous_user_gets_401(self):
        response = self.client.get(
            reverse("api-current-user"),
        )

        self.assertEqual(
            response.status_code,
            401,
        )
