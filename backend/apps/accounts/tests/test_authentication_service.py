from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from apps.accounts.services.authentication import AuthenticationService


User = get_user_model()


class AuthenticationServiceTests(TestCase):
    VALID_PASSWORD = "S3cure-Account-Test-Passphrase!42"

    def test_register_creates_user(self):
        user = AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.check_password(self.VALID_PASSWORD))

    def test_register_normalizes_email(self):
        user = AuthenticationService.register(
            email="  Alice@Example.COM  ",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        self.assertEqual(
            user.email,
            "alice@example.com",
        )

    def test_register_strips_username_whitespace(self):
        user = AuthenticationService.register(
            email="alice@example.com",
            username="  alice  ",
            password=self.VALID_PASSWORD,
        )

        self.assertEqual(user.username, "alice")

    def test_register_rejects_duplicate_email(self):
        AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        with self.assertRaises(ValidationError) as context:
            AuthenticationService.register(
                email="alice@example.com",
                username="bob",
                password=self.VALID_PASSWORD,
            )

        self.assertIn(
            "email",
            context.exception.message_dict,
        )

        self.assertFalse(
            User.objects.filter(
                username="bob",
            ).exists()
        )

    def test_register_rejects_duplicate_username(self):
        AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        with self.assertRaises(ValidationError) as context:
            AuthenticationService.register(
                email="bob@example.com",
                username="alice",
                password=self.VALID_PASSWORD,
            )

        self.assertIn(
            "username",
            context.exception.message_dict,
        )

        self.assertFalse(
            User.objects.filter(
                email="bob@example.com",
            ).exists()
        )

    def test_register_rejects_weak_password(self):
        with self.assertRaises(ValidationError) as context:
            AuthenticationService.register(
                email="alice@example.com",
                username="alice",
                password="123",
            )

        self.assertIn(
            "password",
            context.exception.message_dict,
        )

        self.assertFalse(
            User.objects.filter(
                email="alice@example.com",
            ).exists()
        )

    def test_authenticate_returns_user_for_valid_credentials(self):
        user = AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        authenticated_user = AuthenticationService.authenticate(
            email="alice@example.com",
            password=self.VALID_PASSWORD,
        )

        self.assertEqual(authenticated_user, user)

    def test_authenticate_returns_none_for_wrong_password(self):
        AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        authenticated_user = AuthenticationService.authenticate(
            email="alice@example.com",
            password="Wrong-Password!123",
        )

        self.assertIsNone(authenticated_user)

    def test_authenticate_returns_none_for_unknown_email(self):
        authenticated_user = AuthenticationService.authenticate(
            email="unknown@example.com",
            password=self.VALID_PASSWORD,
        )

        self.assertIsNone(authenticated_user)

    def test_authenticate_does_not_normalize_email_case(self):
        AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        authenticated_user = AuthenticationService.authenticate(
            email="Alice@Example.COM",
            password=self.VALID_PASSWORD,
        )

        self.assertIsNone(authenticated_user)

    def test_authenticate_does_not_strip_email_whitespace(self):
        AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        authenticated_user = AuthenticationService.authenticate(
            email=" alice@example.com ",
            password=self.VALID_PASSWORD,
        )

        self.assertIsNone(authenticated_user)

    def test_logout_removes_authenticated_session(self):
        user = AuthenticationService.register(
            email="alice@example.com",
            username="alice",
            password=self.VALID_PASSWORD,
        )

        request = RequestFactory().get("/")

        middleware = SessionMiddleware(
            lambda request: None
        )
        middleware.process_request(request)
        request.session.save()

        django_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        self.assertIn(
            "_auth_user_id",
            request.session,
        )

        AuthenticationService.logout(
            request=request
        )

        self.assertNotIn(
            "_auth_user_id",
            request.session,
        )
