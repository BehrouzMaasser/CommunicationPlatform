from django.test import TestCase

from apps.accounts.forms.login_form import UserLoginForm
from apps.accounts.forms.signup_form import UserSignupForm


class UserSignupFormTests(TestCase):

    def test_valid_signup_form(self):
        form = UserSignupForm(
            data={
                "email": "alice@example.com",
                "username": "alice",
                "password": "Strong-Password!123",
                "confirm_password": "Strong-Password!123",
            }
        )

        self.assertTrue(form.is_valid())

    def test_email_is_required(self):
        form = UserSignupForm(
            data={
                "email": "",
                "username": "alice",
                "password": "Strong-Password!123",
                "confirm_password": "Strong-Password!123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_username_is_required(self):
        form = UserSignupForm(
            data={
                "email": "alice@example.com",
                "username": "",
                "password": "Strong-Password!123",
                "confirm_password": "Strong-Password!123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_password_is_required(self):
        form = UserSignupForm(
            data={
                "email": "alice@example.com",
                "username": "alice",
                "password": "",
                "confirm_password": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)
        self.assertIn("confirm_password", form.errors)

    def test_passwords_must_match(self):
        form = UserSignupForm(
            data={
                "email": "alice@example.com",
                "username": "alice",
                "password": "Strong-Password!123",
                "confirm_password": "Different-Password!456",
            }
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "password",
            form.errors,
        )

        self.assertIn(
            "confirm_password",
            form.errors,
        )

    def test_password_fields_use_password_widgets(self):
        form = UserSignupForm()

        self.assertEqual(
            form.fields["password"].widget.input_type,
            "password",
        )

        self.assertEqual(
            form.fields["confirm_password"].widget.input_type,
            "password",
        )

    def test_password_fields_do_not_strip_whitespace(self):
        form = UserSignupForm(
            data={
                "email": "alice@example.com",
                "username": "alice",
                "password": " Strong-Password!123 ",
                "confirm_password": " Strong-Password!123 ",
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["password"],
            " Strong-Password!123 ",
        )

        self.assertEqual(
            form.cleaned_data["confirm_password"],
            " Strong-Password!123 ",
        )


class UserLoginFormTests(TestCase):

    def test_valid_login_form(self):
        form = UserLoginForm(
            data={
                "email": "alice@example.com",
                "password": "Strong-Password!123",
            }
        )

        self.assertTrue(form.is_valid())

    def test_email_is_required(self):
        form = UserLoginForm(
            data={
                "email": "",
                "password": "Strong-Password!123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_must_have_valid_format(self):
        form = UserLoginForm(
            data={
                "email": "not-an-email",
                "password": "Strong-Password!123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_is_required(self):
        form = UserLoginForm(
            data={
                "email": "alice@example.com",
                "password": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_password_uses_password_widget(self):
        form = UserLoginForm()

        self.assertEqual(
            form.fields["password"].widget.input_type,
            "password",
        )

    def test_login_email_is_not_stripped(self):
        email_with_spacing = " alice@example.com "
        form = UserLoginForm(
            data={
                "email": email_with_spacing,
                "password": "Strong-Password!123",
            }
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "email",
            form.errors
        )

        self.assertEqual(
            form["email"].value(),
            email_with_spacing
        )

    def test_login_email_case_is_preserved(self):
        form = UserLoginForm(
            data={
                "email": "Alice@Example.COM",
                "password": "Strong-Password!123",
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["email"],
            "Alice@Example.COM",
        )

    def test_login_password_is_not_stripped(self):
        form = UserLoginForm(
            data={
                "email": "alice@example.com",
                "password": " Strong-Password!123 ",
            }
        )

        self.assertTrue(form.is_valid())

        self.assertEqual(
            form.cleaned_data["password"],
            " Strong-Password!123 ",
        )
