import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.conversations.models import GroupConversation


class VoiceSession(models.Model):

    class Kind(models.TextChoices):
        DIRECT = "DIRECT", "Direct call"
        GROUP = "GROUP", "Group voice"

    class Status(models.TextChoices):
        RINGING = "RINGING", "Ringing"
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    class EndReason(models.TextChoices):
        HANGUP = "HANGUP", "Hangup"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        MISSED = "MISSED", "Missed"
        EMPTY = "EMPTY", "Room empty"
        ACCESS_REVOKED = "ACCESS_REVOKED", "Access revoked"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    kind = models.CharField(
        max_length=6,
        choices=Kind.choices,
    )

    status = models.CharField(
        max_length=7,
        choices=Status.choices,
    )

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="started_voice_sessions",
        null=True,
        blank=True,
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_voice_sessions",
        null=True,
        blank=True,
    )

    group = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="voice_sessions",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    ring_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    end_reason = models.CharField(
        max_length=14,
        choices=EndReason.choices,
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["kind", "status"],
                name="voice_session_kind_status_idx",
            ),
            models.Index(
                fields=["group", "status"],
                name="voice_session_group_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        kind="DIRECT",
                        caller__isnull=False,
                        recipient__isnull=False,
                        group__isnull=True,
                        ring_expires_at__isnull=False,
                    )
                    | Q(
                        kind="GROUP",
                        caller__isnull=True,
                        recipient__isnull=True,
                        group__isnull=False,
                        ring_expires_at__isnull=True,
                    )
                ),
                name="voice_session_shape_matches_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="GROUP")
                    | ~Q(caller=F("recipient"))
                ),
                name="voice_direct_users_are_different",
            ),
            models.CheckConstraint(
                condition=~Q(
                    kind="GROUP",
                    status="RINGING",
                ),
                name="voice_group_session_not_ringing",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="RINGING",
                        activated_at__isnull=True,
                        ended_at__isnull=True,
                        end_reason__isnull=True,
                    )
                    | Q(
                        status="ACTIVE",
                        activated_at__isnull=False,
                        ended_at__isnull=True,
                        end_reason__isnull=True,
                    )
                    | Q(
                        status="ENDED",
                        ended_at__isnull=False,
                        end_reason__isnull=False,
                    )
                ),
                name="voice_session_status_timestamps_match",
            ),
            models.UniqueConstraint(
                fields=["group"],
                condition=Q(
                    kind="GROUP",
                    status="ACTIVE",
                ),
                name="unique_active_voice_session_per_group",
            ),
        ]

    @property
    def media_room_name(self) -> str:
        return f"voice_{self.pk.hex}"

    def __str__(self):
        return f"{self.kind} voice session {self.pk} ({self.status})"


class VoiceParticipation(models.Model):

    class Role(models.TextChoices):
        CALLER = "CALLER", "Caller"
        CALLEE = "CALLEE", "Callee"
        MEMBER = "MEMBER", "Group member"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        VoiceSession,
        on_delete=models.CASCADE,
        related_name="participations",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="voice_participations",
    )

    role = models.CharField(
        max_length=6,
        choices=Role.choices,
    )

    client_instance_id = models.UUIDField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    left_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "left_at"],
                name="vp_user_open_idx",
            ),
            models.Index(
                fields=["session", "left_at"],
                name="vp_session_open_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="unique_voice_participation_per_session_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(left_at__isnull=True),
                name="unique_open_voice_participation_per_user",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        client_instance_id__isnull=True,
                        claimed_at__isnull=True,
                    )
                    | Q(
                        client_instance_id__isnull=False,
                        claimed_at__isnull=False,
                    )
                ),
                name="voice_participation_claim_fields_match",
            ),
        ]

    @property
    def media_participant_identity(self) -> str:
        return f"voice_participant_{self.pk.hex}"

    @property
    def is_open(self) -> bool:
        return self.left_at is None

    def __str__(self):
        return f"{self.user_id} in voice session {self.session_id}"
