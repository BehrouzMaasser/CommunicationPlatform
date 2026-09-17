from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

import uuid


class DirectConversation(models.Model):

    user_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_as_user_1",
    )

    user_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_as_user_2",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(user_1__lt=F("user_2")),
                name="direct_conversation_pair_is_canonical",
            ),
            models.UniqueConstraint(
                fields=["user_1", "user_2"],
                name="unique_direct_conversation_pair",
            ),
        ]

    def __str__(self):
        return f"DM: {self.user_1.username} <-> {self.user_2.username}"


def group_avatar_upload_to(instance, filename):
    del filename

    return (
        f"group_avatars/"
        f"{instance.pk}/"
        f"{uuid.uuid4().hex}.webp"
    )


class GroupConversation(models.Model):

    name = models.CharField(max_length=25)

    avatar = models.ImageField(
        upload_to=group_avatar_upload_to,
        blank=True,
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="GroupMembership",
        related_name="group_conversations",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return self.name


class GroupMembership(models.Model):

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MEMBER = "MEMBER", "Member"

    group = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )

    role = models.CharField(
        max_length=6,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                name="unique_group_membership",
            ),
            models.UniqueConstraint(
                fields=["group"],
                condition=Q(role="OWNER"),
                name="unique_group_owner",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class GroupInvitation(models.Model):

    group = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_group_invitations",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_group_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(invited_by=F("recipient")),
                name="group_invitation_users_are_different",
            ),
            models.UniqueConstraint(
                fields=["group", "recipient"],
                name="unique_pending_group_invitation",
            ),
        ]

    def __str__(self):
        return (
            f"{self.invited_by.username} invited "
            f"{self.recipient.username} to {self.group.name}"
        )


class GroupInvitationLink(models.Model):

    group = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="invitation_links",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_group_invitation_links",
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Invitation link for {self.group.name}"
