from django import forms

from apps.accounts.models import User


class UserSignupForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        required=True,
        strip=False,
        widget=forms.PasswordInput,
        help_text="Choose a strong password that isn't easy to guess.",
    )

    confirm_password = forms.CharField(
        label="Confirm password",
        required=True,
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User

        fields = [
            "email",
            "username",
            "password",
            "confirm_password",
        ]

        help_texts = {
            "username": "This is your public identifier.",
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if (
            password
            and confirm_password
            and password != confirm_password
        ):
            self.add_error(
                "password",
                "Passwords must match.",
            )

            self.add_error(
                "confirm_password",
                "Passwords must match.",
            )

        return cleaned_data
