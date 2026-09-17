import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


def user_avatar_upload_to(instance, filename):
    del filename

    return (
        f"user_avatars/"
        f"{instance.pk}/"
        f"{uuid.uuid4().hex}.webp"
    )


class User(AbstractUser):

    email = models.EmailField(
        unique=True,
    )

    avatar = models.ImageField(
        upload_to=user_avatar_upload_to,
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
