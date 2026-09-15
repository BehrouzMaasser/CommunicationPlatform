# Generated for Communication Platform v1.1.0 voice domain.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("conversations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoiceSession",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("DIRECT", "Direct call"),
                            ("GROUP", "Group voice"),
                        ],
                        max_length=6,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("RINGING", "Ringing"),
                            ("ACTIVE", "Active"),
                            ("ENDED", "Ended"),
                        ],
                        max_length=7,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "ring_expires_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "end_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("HANGUP", "Hangup"),
                            ("REJECTED", "Rejected"),
                            ("CANCELLED", "Cancelled"),
                            ("MISSED", "Missed"),
                            ("EMPTY", "Room empty"),
                            ("ACCESS_REVOKED", "Access revoked"),
                        ],
                        max_length=14,
                        null=True,
                    ),
                ),
                (
                    "caller",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="started_voice_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voice_sessions",
                        to="conversations.groupconversation",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_voice_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["kind", "status"],
                        name="voice_session_kind_status_idx",
                    ),
                    models.Index(
                        fields=["group", "status"],
                        name="voice_session_group_status_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ("caller__isnull", False),
                                ("group__isnull", True),
                                ("kind", "DIRECT"),
                                ("recipient__isnull", False),
                                ("ring_expires_at__isnull", False),
                            )
                            | models.Q(
                                ("caller__isnull", True),
                                ("group__isnull", False),
                                ("kind", "GROUP"),
                                ("recipient__isnull", True),
                                ("ring_expires_at__isnull", True),
                            )
                        ),
                        name="voice_session_shape_matches_kind",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(("kind", "GROUP"))
                            | ~models.Q(("caller", models.F("recipient")))
                        ),
                        name="voice_direct_users_are_different",
                    ),
                    models.CheckConstraint(
                        condition=~models.Q(
                            ("kind", "GROUP"),
                            ("status", "RINGING"),
                        ),
                        name="voice_group_session_not_ringing",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ("activated_at__isnull", True),
                                ("end_reason__isnull", True),
                                ("ended_at__isnull", True),
                                ("status", "RINGING"),
                            )
                            | models.Q(
                                ("activated_at__isnull", False),
                                ("end_reason__isnull", True),
                                ("ended_at__isnull", True),
                                ("status", "ACTIVE"),
                            )
                            | models.Q(
                                ("end_reason__isnull", False),
                                ("ended_at__isnull", False),
                                ("status", "ENDED"),
                            )
                        ),
                        name="voice_session_status_timestamps_match",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(
                            ("kind", "GROUP"),
                            ("status", "ACTIVE"),
                        ),
                        fields=("group",),
                        name="unique_active_voice_session_per_group",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="VoiceParticipation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("CALLER", "Caller"),
                            ("CALLEE", "Callee"),
                            ("MEMBER", "Group member"),
                        ],
                        max_length=6,
                    ),
                ),
                ("client_instance_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participations",
                        to="voice.voicesession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voice_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["user", "left_at"],
                        name="vp_user_open_idx",
                    ),
                    models.Index(
                        fields=["session", "left_at"],
                        name="vp_session_open_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("session", "user"),
                        name="unique_voice_participation_per_session_user",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("left_at__isnull", True)),
                        fields=("user",),
                        name="unique_open_voice_participation_per_user",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ("claimed_at__isnull", True),
                                ("client_instance_id__isnull", True),
                            )
                            | models.Q(
                                ("claimed_at__isnull", False),
                                ("client_instance_id__isnull", False),
                            )
                        ),
                        name="voice_participation_claim_fields_match",
                    ),
                ],
            },
        ),
    ]
