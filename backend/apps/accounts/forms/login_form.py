from django import forms
from django.core.validators import validate_email

from apps.accounts.models import User


class UserLoginForm(forms.Form):

    email = forms.CharField(
        label="Email",
        strip=False,
        validators=[validate_email],
        widget=forms.EmailInput,
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
    )
