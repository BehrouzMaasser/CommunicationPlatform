from django import forms
from apps.accounts.models import User


class UserLoginForm(forms.Form):

    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
