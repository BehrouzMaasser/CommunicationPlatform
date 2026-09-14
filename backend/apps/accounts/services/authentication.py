from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


User = get_user_model()


class AuthenticationService:

    @staticmethod
    def _registration_conflict_errors(
        *,
        email: str,
        username: str,
    ) -> dict[str, str]:
        field_errors: dict[str, str] = {}

        if User.objects.filter(username=username).exists():
            field_errors["username"] = "Username already exists."

        if User.objects.filter(email=email).exists():
            field_errors["email"] = "Email already exists."

        return field_errors

    @staticmethod
    def register(*, email: str, username: str, password: str) -> User:

        email = email.strip().lower()
        username = username.strip()

        field_errors = AuthenticationService._registration_conflict_errors(
            email=email,
            username=username,
        )

        if field_errors:
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

        try:
            # Keep the unique-constraint failure inside a savepoint so the
            # connection remains usable when register() itself is called from
            # a larger transaction. The database remains the final authority
            # under concurrent registrations.
            with transaction.atomic():
                user.save()
        except IntegrityError as exc:
            field_errors = AuthenticationService._registration_conflict_errors(
                email=email,
                username=username,
            )

            if field_errors:
                raise ValidationError(field_errors) from exc

            # Do not hide unrelated database integrity failures.
            raise

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
