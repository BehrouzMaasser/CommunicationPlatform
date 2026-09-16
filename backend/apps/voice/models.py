import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from uuid6 import uuid7

from apps.conversations.models import GroupConversation


class VoiceRoom(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
    )

    name = models.CharField(
        max_length=50,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_voice_rooms",
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="VoiceRoomMembership",
        related_name="voice_rooms",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name


class VoiceRoomMembership(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
    )

    room = models.ForeignKey(
        VoiceRoom,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="voice_room_memberships",
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name="unique_voice_room_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} in voice room {self.room_id}"


class VoiceRoomInvitation(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
    )

    room = models.ForeignKey(
        VoiceRoom,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_voice_room_invitations",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_voice_room_invitations",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(
                    invited_by=F("recipient"),
                ),
                name="voice_room_invitation_users_different",
            ),
            models.UniqueConstraint(
                fields=["room", "recipient"],
                name="unique_pending_voice_room_invitation",
            ),
        ]

    def __str__(self):
        return (
            f"{self.invited_by_id} invited "
            f"{self.recipient_id} to voice room "
            f"{self.room_id}"
        )


class VoiceRoomInvitationLink(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
    )

    room = models.ForeignKey(
        VoiceRoom,
        on_delete=models.CASCADE,
        related_name="invitation_links",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_voice_room_invitation_links",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        db_index=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Invitation link for voice room {self.room_id}"


class VoiceSession(models.Model):

    class Kind(models.TextChoices):
        DIRECT = "DIRECT", "Direct call"
        GROUP = "GROUP", "Legacy group voice"
        ROOM = "ROOM", "Voice room"

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

    voice_room = models.ForeignKey(
        "VoiceRoom",
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
            models.Index(
                fields=["voice_room", "status"],
                name="voice_session_room_status_idx",
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
                        voice_room__isnull=True,
                        ring_expires_at__isnull=False,
                    )
                    | Q(
                        kind="GROUP",
                        caller__isnull=True,
                        recipient__isnull=True,
                        group__isnull=False,
                        voice_room__isnull=True,
                        ring_expires_at__isnull=True,
                    )
                    | Q(
                        kind="ROOM",
                        caller__isnull=True,
                        recipient__isnull=True,
                        group__isnull=True,
                        voice_room__isnull=False,
                        ring_expires_at__isnull=True,
                    )
                ),
                name="voice_session_shape_matches_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind__in=["GROUP", "ROOM"])
                    | ~Q(caller=F("recipient"))
                ),
                name="voice_direct_users_are_different",
            ),
            models.CheckConstraint(
                condition=~Q(
                    kind__in=["GROUP", "ROOM"],
                    status="RINGING",
                ),
                name="voice_nondirect_session_not_ringing",
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
            models.UniqueConstraint(
                fields=["voice_room"],
                condition=Q(
                    kind="ROOM",
                    status="ACTIVE",
                ),
                name="unique_active_voice_session_per_room",
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
