from django import forms
from apps.accounts.models import User


class UserSignupForm(forms.ModelForm):

    confirm_password = forms.CharField(required=True)

    class Meta:
        widgets = {
            "password": forms.PasswordInput(),
            "confirm_password": forms.PasswordInput(),
        }

        model = User
        fields = [
            "email",
            "username",
            "password",
            "confirm_password",
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError(
                    {
                        "confirm_password": "Passwords must match.",
                        "password": "Passwords must match.",
                    }
                )

        return cleaned_data
