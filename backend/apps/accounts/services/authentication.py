from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q


User = get_user_model()


class AuthenticationService:

    @staticmethod
    def register(*, email: str, username: str, password: str) -> User:

        email = email.strip().lower()
        username = username.strip()

        existing_query = User.objects.filter(Q(email=email) | Q(username=username))

        field_errors = {}

        if existing_query.exists():
            if existing_query.filter(username=username).exists():
                field_errors["username"] = "Username already exists."

            if existing_query.filter(email=email).exists():
                field_errors["email"] = "Email already exists."

            raise ValidationError(field_errors)

        user = User(
            email=email,
            username=username,
        )

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise ValidationError(
                {"password": exc.messages}
            ) from exc

        user.set_password(password)
        user.save()

        return user

    @staticmethod
    def authenticate(*, email: str, password: str) -> User | None:

        return authenticate(
            email=email,
            password=password,
        )

    @staticmethod
    def logout(*, request) -> None:

        logout(request)
