from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from apps.accounts.forms.login_form import UserLoginForm
from apps.accounts.forms.signup_form import UserSignupForm
from apps.accounts.services.authentication import AuthenticationService


def _allowed_redirect_hosts(request) -> set[str]:
    allowed_hosts = {request.get_host()}

    configured_urls = [
        settings.FRONTEND_BASE_URL,
        *getattr(settings, "CORS_ALLOWED_ORIGINS", []),
        *getattr(settings, "CSRF_TRUSTED_ORIGINS", []),
    ]

    for configured_url in configured_urls:
        host = urlsplit(configured_url).netloc
        if host:
            allowed_hosts.add(host)

    return allowed_hosts


def _safe_next_url(request) -> str:
    candidate = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()

    if not candidate:
        return ""

    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts=_allowed_redirect_hosts(request),
        require_https=request.is_secure(),
    ):
        return ""

    return candidate


def _default_frontend_url() -> str:
    return f"{settings.FRONTEND_BASE_URL}/"


def _redirect_after_auth(request):
    next_url = _safe_next_url(request)
    if next_url:
        return redirect(next_url)

    return redirect(_default_frontend_url())


def _auth_context(*, form, next_url: str) -> dict:
    return {
        "form": form,
        "frontend_base_url": settings.FRONTEND_BASE_URL,
        "next_url": next_url,
    }


class SignupView(View):

    template_name = "accounts/signup.html"

    def get(self, request):
        next_url = _safe_next_url(request)

        if request.user.is_authenticated:
            return _redirect_after_auth(request)

        return render(
            request,
            self.template_name,
            _auth_context(
                form=UserSignupForm(),
                next_url=next_url,
            ),
        )

    def post(self, request):
        next_url = _safe_next_url(request)
        form = UserSignupForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                _auth_context(
                    form=form,
                    next_url=next_url,
                ),
            )

        try:
            user = AuthenticationService.register(
                email=form.cleaned_data["email"],
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )

            login(request, user)

            return _redirect_after_auth(request)

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
            _auth_context(
                form=form,
                next_url=next_url,
            ),
        )


class LoginView(View):

    template_name = "accounts/login.html"

    def get(self, request):
        next_url = _safe_next_url(request)

        if request.user.is_authenticated:
            return _redirect_after_auth(request)

        return render(
            request,
            self.template_name,
            _auth_context(
                form=UserLoginForm(),
                next_url=next_url,
            ),
        )

    def post(self, request):
        next_url = _safe_next_url(request)
        form = UserLoginForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                _auth_context(
                    form=form,
                    next_url=next_url,
                ),
            )

        user = AuthenticationService.authenticate(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )

        if user:
            login(request, user)

            return _redirect_after_auth(request)

        form.add_error(None, "Invalid credentials.")

        return render(
            request,
            self.template_name,
            _auth_context(
                form=form,
                next_url=next_url,
            ),
        )


class LogoutView(LoginRequiredMixin, View):

    def post(self, request):
        AuthenticationService.logout(request=request)

        return redirect("auth-login")
