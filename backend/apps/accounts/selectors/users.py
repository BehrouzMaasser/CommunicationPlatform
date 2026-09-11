from django.contrib.auth import get_user_model
from django.db.models import QuerySet


User = get_user_model()


class UserSelector:

    @staticmethod
    def search_public_users(
        *,
        current_user: User,
        search: str,
    ) -> QuerySet[User]:
        if not search:
            return User.objects.none()

        return (
            User.objects
            .filter(
                username__icontains=search,
            )
            .exclude(pk=current_user.pk)
            .order_by(
                "username",
                "pk",
            )
        )
