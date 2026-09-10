from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AccountViewTests(TestCase):
    VALID_PASSWORD = "S3cure-Account-Test-Passphrase!42"

    def setUp(self):
        self.user = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_register_page_is_accessible_to_anonymous_user(self):
        response = self.client.get(
            reverse("auth-register")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/signup.html",
        )

    def test_register_creates_user_and_logs_them_in(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "bob@example.com",
                "username": "bob",
                "password": self.VALID_PASSWORD,
                "confirm_password": self.VALID_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("users-me"),
        )

        user = User.objects.get(
            email="bob@example.com"
        )

        self.assertEqual(user.username, "bob")
        self.assertTrue(
            user.check_password(self.VALID_PASSWORD)
        )

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            user.pk,
        )

    def test_register_with_invalid_data_does_not_create_user(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "bob@example.com",
                "username": "bob",
                "password": "Password-One!123",
                "confirm_password": "Password-Two!123",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                email="bob@example.com",
            ).exists()
        )

    def test_authenticated_user_cannot_access_register_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("auth-register")
        )

        self.assertRedirects(
            response,
            reverse("users-me"),
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def test_login_page_is_accessible_to_anonymous_user(self):
        response = self.client.get(
            reverse("auth-login")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/login.html",
        )

    def test_login_with_valid_credentials_authenticates_user(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "email": "alice@example.com",
                "password": self.VALID_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("users-me"),
        )

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.pk,
        )

    def test_login_with_invalid_password_does_not_authenticate_user(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "email": "alice@example.com",
                "password": "Wrong-Password!123",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_authenticated_user_cannot_access_login_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("auth-login")
        )

        self.assertRedirects(
            response,
            reverse("users-me"),
        )

    # ------------------------------------------------------------------
    # Current user
    # ------------------------------------------------------------------

    def test_me_requires_authentication(self):
        response = self.client.get(
            reverse("users-me")
        )

        expected_login_url = (
            f"{reverse('auth-login')}"
            f"?next={reverse('users-me')}"
        )

        self.assertRedirects(
            response,
            expected_login_url,
        )

    def test_me_is_accessible_to_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("users-me")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/me.html",
        )

        self.assertEqual(
            response.context["user"],
            self.user,
        )

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def test_logout_logs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("auth-logout")
        )

        self.assertRedirects(
            response,
            reverse("auth-login"),
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_does_not_allow_get(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("auth-logout")
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_logout_requires_authentication(self):
        response = self.client.post(
            reverse("auth-logout")
        )

        expected_login_url = (
            f"{reverse('auth-login')}"
            f"?next={reverse('auth-logout')}"
        )

        self.assertRedirects(
            response,
            expected_login_url,
        )
