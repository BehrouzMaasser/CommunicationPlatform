from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Least, Greatest


class FriendRequest(models.Model):

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(sender=models.F("recipient")),
                name="friend_request_sender_not_recipient",
                violation_error_code="sender_is_the_recipient"
            ),
            models.UniqueConstraint(
                Least("sender_id", "recipient_id"),
                Greatest("sender_id", "recipient_id"),
                name="unique_pending_friend_request_pair",
                violation_error_code="request_is_sent_and_is_pending"
            ),
        ]


    def __str__(self):
        return f"{self.sender} -> {self.recipient}"


class Friendship(models.Model):

    user_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_user_1",
    )
    user_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_user_2",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(user_1__lt=F("user_2")),
                name="friendship_pair_is_canonical",
            ),

            models.UniqueConstraint(
                fields=["user_1", "user_2"],
                name="unique_friendship_pair",
            ),
        ]

    def __str__(self):
        return f"{self.user_1} <-> {self.user_2}"
