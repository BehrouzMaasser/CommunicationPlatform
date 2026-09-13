from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views import View

from apps.accounts.services.authentication import AuthenticationService
from apps.accounts.forms.signup_form import UserSignupForm
from apps.accounts.forms.login_form import UserLoginForm


class SignupView(View):

    template_name = "accounts/signup.html"

    def get(self, request):

        if request.user.is_authenticated:

            return redirect(f"{settings.FRONTEND_BASE_URL}/")

        return render(
            request,
            self.template_name,
            {
                "form": UserSignupForm(),
                "frontend_base_url": settings.FRONTEND_BASE_URL,
            },
        )

    def post(self, request):

        form = UserSignupForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "frontend_base_url": settings.FRONTEND_BASE_URL,
                },
            )

        try:
            user = AuthenticationService.register(
                email=form.cleaned_data["email"],
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )

            login(request, user)

            return redirect(f"{settings.FRONTEND_BASE_URL}/")

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, messages_ in e.message_dict.items():
                    for message in messages_:
                        form.add_error(field, message)
            else:
                form.add_error(None, e.message)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "frontend_base_url": settings.FRONTEND_BASE_URL,
            },
        )


class LoginView(View):

    template_name = "accounts/login.html"

    def get(self, request):

        if request.user.is_authenticated:

            return redirect(f"{settings.FRONTEND_BASE_URL}/")

        return render(
            request,
            self.template_name,
            {
                "form": UserLoginForm(),
                "frontend_base_url": settings.FRONTEND_BASE_URL,
            },
        )

    def post(self, request):

        form = UserLoginForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "frontend_base_url": settings.FRONTEND_BASE_URL,
                },
            )

        user = AuthenticationService.authenticate(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"]
        )

        if user:
            login(request, user)

            return redirect(f"{settings.FRONTEND_BASE_URL}/")

        form.add_error(None, "Invalid credentials.")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "frontend_base_url": settings.FRONTEND_BASE_URL,
            },
        )


class LogoutView(LoginRequiredMixin, View):

    def post(self, request):

        AuthenticationService.logout(request=request)

        return redirect("auth-login")
