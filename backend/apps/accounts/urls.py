from django.urls import path

from apps.accounts.views.authentication import (
    SignupView,
    LoginView,
    LogoutView,
)

from apps.accounts.views.users import (
    CurrentUserView
)


urlpatterns = [
    path(
        "register/",
        SignupView.as_view(),
        name="auth-register",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="auth-login",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="auth-logout",
    ),
]

urlpatterns += [
    path(
        "me/",
        CurrentUserView.as_view(),
        name="users-me",
    )
]
