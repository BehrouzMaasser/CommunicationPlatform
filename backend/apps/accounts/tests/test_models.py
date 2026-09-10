from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


User = get_user_model()


class UserModelTests(TestCase):

    def test_email_is_authentication_identifier(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_username_is_required_field(self):
        self.assertIn("username", User.REQUIRED_FIELDS)

    def test_user_can_be_created(self):
        user = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="strong-test-password-123",
        )

        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.username, "alice")
        self.assertTrue(
            user.check_password("strong-test-password-123")
        )

    def test_email_must_be_unique(self):
        User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="strong-test-password-123",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="alice@example.com",
                    username="bob",
                    password="strong-test-password-123",
                )

    def test_username_must_be_unique(self):
        User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="strong-test-password-123",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="bob@example.com",
                    username="alice",
                    password="strong-test-password-123",
                )
