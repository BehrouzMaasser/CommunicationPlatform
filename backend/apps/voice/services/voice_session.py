import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.voice.exceptions import (
    SelfVoiceCallNotAllowed,
    VoiceCallPermissionDenied,
    VoiceFriendshipRequired,
    VoiceGroupMembershipRequired,
    VoiceGroupNotFound,
    VoiceInvalidState,
    VoiceParticipationClaimed,
    VoiceParticipationNotActive,
    VoiceSessionNotFound,
    VoiceTargetUserNotFound,
    VoiceUserBusy,
)
from apps.voice.models import (
    VoiceParticipation,
    VoiceRoomMembership,
    VoiceSession,
)
from apps.voice.realtime import VoiceRealtimePublisher
from apps.voice.services.media_cleanup import VoiceMediaCleanup
from apps.voice.services.voice_room import VoiceRoomService


User = get_user_model()


class VoiceSessionService:
    """Authoritative lifecycle operations for direct and group voice."""

    @staticmethod
    def normalize_client_instance_id(value) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        if value is None:
            raise ValueError("client_instance_id is required.")

        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(
                "client_instance_id must be a valid UUID."
            ) from exc

    @staticmethod
    def _lock_users(*, user_ids: list[int]) -> dict[int, User]:
        users = list(
            User.objects
            .select_for_update()
            .filter(pk__in=user_ids)
            .order_by("pk")
        )

        return {
            user.pk: user
            for user in users
        }

    @staticmethod
    def _group_member_user_ids(*, group_id: int) -> list[int]:
        return list(
            GroupMembership.objects
            .filter(group_id=group_id)
            .values_list("user_id", flat=True)
        )

    @staticmethod
    def _voice_room_member_user_ids(
        *,
        room_id,
    ) -> list[int]:
        return list(
            VoiceRoomMembership.objects
            .filter(room_id=room_id)
            .values_list("user_id", flat=True)
        )

    @staticmethod
    def _get_direct_session_for_update(*, session_id) -> VoiceSession:
        session = (
            VoiceSession.objects
            .select_for_update()
            .filter(
                pk=session_id,
                kind=VoiceSession.Kind.DIRECT,
            )
            .first()
        )

        if session is None:
            raise VoiceSessionNotFound

        return session

    @staticmethod
    def _require_open_participation_for_update(
        *,
        session: VoiceSession,
        user_id: int,
    ) -> VoiceParticipation:
        participation = (
            VoiceParticipation.objects
            .select_for_update()
            .filter(
                session=session,
                user_id=user_id,
                left_at__isnull=True,
            )
            .first()
        )

        if participation is None:
            raise VoiceParticipationNotActive

        return participation

    @staticmethod
    def _require_client_owner(
        *,
        participation: VoiceParticipation,
        client_instance_id: uuid.UUID,
    ) -> None:
        if participation.client_instance_id != client_instance_id:
            raise VoiceParticipationClaimed

    @staticmethod
    def _finish_session_locked(
        *,
        session: VoiceSession,
        end_reason: str,
    ) -> VoiceSession:
        now = timezone.now()

        VoiceParticipation.objects.filter(
            session=session,
            left_at__isnull=True,
        ).update(
            left_at=now,
        )

        session.status = VoiceSession.Status.ENDED
        session.ended_at = now
        session.end_reason = end_reason
        session.save(
            update_fields=[
                "status",
                "ended_at",
                "end_reason",
            ]
        )

        return session

    @classmethod
    def _expire_due_direct_calls_for_users_locked(
        cls,
        *,
        user_ids: list[int],
    ) -> None:
        now = timezone.now()
        session_ids = list(
            VoiceParticipation.objects
            .filter(
                user_id__in=user_ids,
                left_at__isnull=True,
                session__kind=VoiceSession.Kind.DIRECT,
                session__status=VoiceSession.Status.RINGING,
                session__ring_expires_at__lte=now,
            )
            .values_list(
                "session_id",
                flat=True,
            )
            .distinct()
        )

        if not session_ids:
            return

        sessions = list(
            VoiceSession.objects
            .select_for_update()
            .filter(
                pk__in=session_ids,
                kind=VoiceSession.Kind.DIRECT,
                status=VoiceSession.Status.RINGING,
                ring_expires_at__lte=now,
            )
            .order_by(
                "created_at",
                "pk",
            )
        )

        for session in sessions:
            cls._finish_session_locked(
                session=session,
                end_reason=VoiceSession.EndReason.MISSED,
            )
            VoiceRealtimePublisher.direct_call_ended_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )

    @staticmethod
    def _direct_call_is_expired(*, session: VoiceSession) -> bool:
        return (
            session.status == VoiceSession.Status.RINGING
            and session.ring_expires_at is not None
            and session.ring_expires_at <= timezone.now()
        )

    @classmethod
    def start_direct_call(
        cls,
        *,
        current_user: User,
        target_user_id: int,
        client_instance_id,
    ) -> VoiceSession:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )

        if current_user.pk == target_user_id:
            raise SelfVoiceCallNotAllowed

        user_ids = sorted(
            [
                current_user.pk,
                target_user_id,
            ]
        )

        with transaction.atomic():
            locked_users = cls._lock_users(
                user_ids=user_ids,
            )

            if target_user_id not in locked_users:
                raise VoiceTargetUserNotFound

            caller = locked_users.get(current_user.pk)
            if caller is None:
                raise VoiceTargetUserNotFound

            recipient = locked_users[target_user_id]
            user_1_id, user_2_id = user_ids

            cls._expire_due_direct_calls_for_users_locked(
                user_ids=user_ids,
            )

            friendship = (
                Friendship.objects
                .select_for_update()
                .filter(
                    user_1_id=user_1_id,
                    user_2_id=user_2_id,
                )
                .first()
            )

            if friendship is None:
                raise VoiceFriendshipRequired

            if (
                VoiceParticipation.objects
                .select_for_update()
                .filter(
                    user_id__in=user_ids,
                    left_at__isnull=True,
                )
                .exists()
            ):
                raise VoiceUserBusy

            now = timezone.now()
            session = VoiceSession.objects.create(
                kind=VoiceSession.Kind.DIRECT,
                status=VoiceSession.Status.RINGING,
                caller=caller,
                recipient=recipient,
                ring_expires_at=(
                    now
                    + timedelta(
                        seconds=settings.VOICE_DIRECT_CALL_RING_TIMEOUT_SECONDS,
                    )
                ),
            )

            try:
                with transaction.atomic():
                    VoiceParticipation.objects.create(
                        session=session,
                        user=caller,
                        role=VoiceParticipation.Role.CALLER,
                        client_instance_id=client_instance_id,
                        claimed_at=now,
                    )

                    VoiceParticipation.objects.create(
                        session=session,
                        user=recipient,
                        role=VoiceParticipation.Role.CALLEE,
                    )
            except IntegrityError as exc:
                raise VoiceUserBusy from exc

            VoiceRealtimePublisher.direct_call_ringing_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                ring_expires_at=session.ring_expires_at,
            )

        return session

    @classmethod
    def accept_direct_call(
        cls,
        *,
        current_user: User,
        session_id,
        client_instance_id,
    ) -> VoiceSession:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )
        expired = False
        transitioned = False
        result = None

        with transaction.atomic():
            session = cls._get_direct_session_for_update(
                session_id=session_id,
            )

            if session.recipient_id != current_user.pk:
                raise VoiceCallPermissionDenied

            if cls._direct_call_is_expired(session=session):
                cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.MISSED,
                )
                expired = True
            else:
                participation = cls._require_open_participation_for_update(
                    session=session,
                    user_id=current_user.pk,
                )

                if session.status == VoiceSession.Status.ACTIVE:
                    cls._require_client_owner(
                        participation=participation,
                        client_instance_id=client_instance_id,
                    )
                    result = session
                elif session.status == VoiceSession.Status.RINGING:
                    if participation.client_instance_id is not None:
                        cls._require_client_owner(
                            participation=participation,
                            client_instance_id=client_instance_id,
                        )
                    else:
                        participation.client_instance_id = client_instance_id
                        participation.claimed_at = timezone.now()
                        participation.save(
                            update_fields=[
                                "client_instance_id",
                                "claimed_at",
                            ]
                        )

                    session.status = VoiceSession.Status.ACTIVE
                    session.activated_at = timezone.now()
                    session.save(
                        update_fields=[
                            "status",
                            "activated_at",
                        ]
                    )
                    transitioned = True
                    result = session
                else:
                    raise VoiceInvalidState

            if expired:
                VoiceRealtimePublisher.direct_call_ended_after_commit(
                    session_id=session.pk,
                    caller_id=session.caller_id,
                    recipient_id=session.recipient_id,
                    end_reason=session.end_reason,
                    ended_at=session.ended_at,
                )
            elif transitioned:
                VoiceRealtimePublisher.direct_call_accepted_after_commit(
                    session_id=session.pk,
                    caller_id=session.caller_id,
                    recipient_id=session.recipient_id,
                    accepted_by_client_instance_id=client_instance_id,
                    activated_at=session.activated_at,
                )

        if expired:
            raise VoiceInvalidState

        return result

    @classmethod
    def reject_direct_call(
        cls,
        *,
        current_user: User,
        session_id,
    ) -> VoiceSession:
        expired = False
        result = None

        with transaction.atomic():
            session = cls._get_direct_session_for_update(
                session_id=session_id,
            )

            if session.recipient_id != current_user.pk:
                raise VoiceCallPermissionDenied

            if cls._direct_call_is_expired(session=session):
                result = cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.MISSED,
                )
                expired = True
            elif session.status != VoiceSession.Status.RINGING:
                raise VoiceInvalidState
            else:
                result = cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.REJECTED,
                )

            VoiceRealtimePublisher.direct_call_ended_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )

        if expired:
            raise VoiceInvalidState

        return result

    @classmethod
    def cancel_direct_call(
        cls,
        *,
        current_user: User,
        session_id,
    ) -> VoiceSession:
        expired = False
        result = None

        with transaction.atomic():
            session = cls._get_direct_session_for_update(
                session_id=session_id,
            )

            if session.caller_id != current_user.pk:
                raise VoiceCallPermissionDenied

            if cls._direct_call_is_expired(session=session):
                result = cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.MISSED,
                )
                expired = True
            elif session.status != VoiceSession.Status.RINGING:
                raise VoiceInvalidState
            else:
                result = cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.CANCELLED,
                )

            VoiceRealtimePublisher.direct_call_ended_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )

        if expired:
            raise VoiceInvalidState

        return result

    @classmethod
    def mark_direct_call_missed(
        cls,
        *,
        session_id,
    ) -> VoiceSession:
        with transaction.atomic():
            session = cls._get_direct_session_for_update(
                session_id=session_id,
            )

            if (
                session.status == VoiceSession.Status.ENDED
                and session.end_reason == VoiceSession.EndReason.MISSED
            ):
                return session

            if session.status != VoiceSession.Status.RINGING:
                raise VoiceInvalidState

            if not cls._direct_call_is_expired(session=session):
                raise VoiceInvalidState

            result = cls._finish_session_locked(
                session=session,
                end_reason=VoiceSession.EndReason.MISSED,
            )
            VoiceRealtimePublisher.direct_call_ended_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )
            return result

    @classmethod
    def end_direct_call(
        cls,
        *,
        current_user: User,
        session_id,
    ) -> VoiceSession:
        with transaction.atomic():
            session = cls._get_direct_session_for_update(
                session_id=session_id,
            )

            if current_user.pk not in {
                session.caller_id,
                session.recipient_id,
            }:
                raise VoiceCallPermissionDenied

            if session.status != VoiceSession.Status.ACTIVE:
                raise VoiceInvalidState

            cls._require_open_participation_for_update(
                session=session,
                user_id=current_user.pk,
            )

            result = cls._finish_session_locked(
                session=session,
                end_reason=VoiceSession.EndReason.HANGUP,
            )
            VoiceMediaCleanup.delete_room_after_commit(
                room_name=session.media_room_name,
            )
            VoiceRealtimePublisher.direct_call_ended_after_commit(
                session_id=session.pk,
                caller_id=session.caller_id,
                recipient_id=session.recipient_id,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )
            return result

    @classmethod
    def reconcile_for_user(
        cls,
        *,
        current_user: User,
    ) -> VoiceParticipation | None:
        """Expire stale rings and return the account's current voice state."""

        with transaction.atomic():
            cls._lock_users(
                user_ids=[current_user.pk],
            )
            cls._expire_due_direct_calls_for_users_locked(
                user_ids=[current_user.pk],
            )

            return (
                VoiceParticipation.objects
                .select_related(
                    "session",
                    "session__caller",
                    "session__recipient",
                    "session__group",
                    "session__voice_room",
                    "user",
                )
                .filter(
                    user=current_user,
                    left_at__isnull=True,
                )
                .first()
            )

    @classmethod
    def join_group_voice(
        cls,
        *,
        current_user: User,
        group_id: int,
        client_instance_id,
    ) -> VoiceParticipation:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )

        with transaction.atomic():
            group = (
                GroupConversation.objects
                .select_for_update()
                .filter(pk=group_id)
                .first()
            )

            if group is None:
                raise VoiceGroupNotFound

            membership = (
                GroupMembership.objects
                .select_for_update()
                .filter(
                    group=group,
                    user=current_user,
                )
                .first()
            )

            if membership is None:
                raise VoiceGroupMembershipRequired

            locked_users = cls._lock_users(
                user_ids=[current_user.pk],
            )
            locked_user = locked_users.get(current_user.pk)

            if locked_user is None:
                raise VoiceParticipationNotActive

            cls._expire_due_direct_calls_for_users_locked(
                user_ids=[current_user.pk],
            )

            existing = (
                VoiceParticipation.objects
                .select_for_update()
                .select_related("session")
                .filter(
                    user=locked_user,
                    left_at__isnull=True,
                )
                .first()
            )

            if existing is not None:
                if (
                    existing.session.kind == VoiceSession.Kind.GROUP
                    and existing.session.group_id == group.pk
                    and existing.session.status == VoiceSession.Status.ACTIVE
                ):
                    cls._require_client_owner(
                        participation=existing,
                        client_instance_id=client_instance_id,
                    )
                    return existing

                raise VoiceUserBusy

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.GROUP,
                    group=group,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                session = VoiceSession.objects.create(
                    kind=VoiceSession.Kind.GROUP,
                    status=VoiceSession.Status.ACTIVE,
                    group=group,
                    activated_at=timezone.now(),
                )

            now = timezone.now()

            try:
                with transaction.atomic():
                    participation = VoiceParticipation.objects.create(
                        session=session,
                        user=locked_user,
                        role=VoiceParticipation.Role.MEMBER,
                        client_instance_id=client_instance_id,
                        claimed_at=now,
                    )
            except IntegrityError as exc:
                raise VoiceUserBusy from exc

            VoiceRealtimePublisher.group_participant_joined_after_commit(
                session_id=session.pk,
                participation_id=participation.pk,
                group_id=group.pk,
                user_id=current_user.pk,
                audience_user_ids=cls._group_member_user_ids(
                    group_id=group.pk,
                ),
            )

        return participation

    @classmethod
    def leave_group_voice(
        cls,
        *,
        current_user: User,
        group_id: int,
        client_instance_id,
    ) -> VoiceSession:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )

        with transaction.atomic():
            group = (
                GroupConversation.objects
                .select_for_update()
                .filter(pk=group_id)
                .first()
            )

            if group is None:
                raise VoiceGroupNotFound

            cls._lock_users(
                user_ids=[current_user.pk],
            )

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.GROUP,
                    group=group,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                raise VoiceParticipationNotActive

            participation = cls._require_open_participation_for_update(
                session=session,
                user_id=current_user.pk,
            )

            cls._require_client_owner(
                participation=participation,
                client_instance_id=client_instance_id,
            )

            participation.left_at = timezone.now()
            participation.save(
                update_fields=["left_at"],
            )

            if not VoiceParticipation.objects.filter(
                session=session,
                left_at__isnull=True,
            ).exists():
                now = timezone.now()
                session.status = VoiceSession.Status.ENDED
                session.ended_at = now
                session.end_reason = VoiceSession.EndReason.EMPTY
                session.save(
                    update_fields=[
                        "status",
                        "ended_at",
                        "end_reason",
                    ]
                )
                VoiceMediaCleanup.delete_room_after_commit(
                    room_name=session.media_room_name,
                )
            else:
                VoiceMediaCleanup.remove_participant_after_commit(
                    room_name=session.media_room_name,
                    participant_identity=(
                        participation.media_participant_identity
                    ),
                )

            VoiceRealtimePublisher.group_participant_left_after_commit(
                session_id=session.pk,
                participation_id=participation.pk,
                group_id=group.pk,
                user_id=current_user.pk,
                audience_user_ids=cls._group_member_user_ids(
                    group_id=group.pk,
                ),
                session_ended=(session.status == VoiceSession.Status.ENDED),
            )

        return session

    @classmethod
    def join_voice_room(
        cls,
        *,
        current_user: User,
        room_id,
        client_instance_id,
    ) -> VoiceParticipation:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )

        with transaction.atomic():
            room = VoiceRoomService._get_room_for_update(
                room_id=room_id,
            )

            VoiceRoomService._get_membership_for_update(
                room=room,
                user=current_user,
            )

            locked_users = cls._lock_users(
                user_ids=[current_user.pk],
            )
            locked_user = locked_users.get(
                current_user.pk
            )

            if locked_user is None:
                raise VoiceParticipationNotActive

            cls._expire_due_direct_calls_for_users_locked(
                user_ids=[current_user.pk],
            )

            existing = (
                VoiceParticipation.objects
                .select_for_update()
                .select_related(
                    "session",
                )
                .filter(
                    user=locked_user,
                    left_at__isnull=True,
                )
                .first()
            )

            if existing is not None:
                if (
                    existing.session.kind
                    == VoiceSession.Kind.ROOM
                    and existing.session.voice_room_id
                    == room.pk
                    and existing.session.status
                    == VoiceSession.Status.ACTIVE
                ):
                    cls._require_client_owner(
                        participation=existing,
                        client_instance_id=client_instance_id,
                    )
                    return existing

                raise VoiceUserBusy

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.ROOM,
                    voice_room=room,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                session = VoiceSession.objects.create(
                    kind=VoiceSession.Kind.ROOM,
                    status=VoiceSession.Status.ACTIVE,
                    voice_room=room,
                    activated_at=timezone.now(),
                )

            now = timezone.now()

            try:
                with transaction.atomic():
                    participation = (
                        VoiceParticipation.objects.create(
                            session=session,
                            user=locked_user,
                            role=VoiceParticipation.Role.MEMBER,
                            client_instance_id=client_instance_id,
                            claimed_at=now,
                        )
                    )
            except IntegrityError as exc:
                raise VoiceUserBusy from exc

            (
                VoiceRealtimePublisher
                .room_participant_joined_after_commit(
                    session_id=session.pk,
                    participation_id=participation.pk,
                    room_id=room.pk,
                    user_id=current_user.pk,
                    audience_user_ids=(
                        cls._voice_room_member_user_ids(
                            room_id=room.pk,
                        )
                    ),
                )
            )

        return participation

    @classmethod
    def leave_voice_room(
        cls,
        *,
        current_user: User,
        room_id,
        client_instance_id,
    ) -> VoiceSession:
        client_instance_id = cls.normalize_client_instance_id(
            client_instance_id
        )

        with transaction.atomic():
            room = VoiceRoomService._get_room_for_update(
                room_id=room_id,
            )

            VoiceRoomService._get_membership_for_update(
                room=room,
                user=current_user,
            )

            cls._lock_users(
                user_ids=[current_user.pk],
            )

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.ROOM,
                    voice_room=room,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                raise VoiceParticipationNotActive

            participation = (
                cls._require_open_participation_for_update(
                    session=session,
                    user_id=current_user.pk,
                )
            )

            cls._require_client_owner(
                participation=participation,
                client_instance_id=client_instance_id,
            )

            participation.left_at = timezone.now()
            participation.save(
                update_fields=["left_at"],
            )

            session_ended = not (
                VoiceParticipation.objects.filter(
                    session=session,
                    left_at__isnull=True,
                ).exists()
            )

            if session_ended:
                cls._finish_session_locked(
                    session=session,
                    end_reason=VoiceSession.EndReason.EMPTY,
                )

                VoiceMediaCleanup.delete_room_after_commit(
                    room_name=session.media_room_name,
                )
            else:
                (
                    VoiceMediaCleanup
                    .remove_participant_after_commit(
                        room_name=session.media_room_name,
                        participant_identity=(
                            participation
                            .media_participant_identity
                        ),
                    )
                )

            (
                VoiceRealtimePublisher
                .room_participant_left_after_commit(
                    session_id=session.pk,
                    participation_id=participation.pk,
                    room_id=room.pk,
                    user_id=current_user.pk,
                    audience_user_ids=(
                        cls._voice_room_member_user_ids(
                            room_id=room.pk,
                        )
                    ),
                    session_ended=session_ended,
                )
            )

        return session

    @classmethod
    def revoke_group_participant(
        cls,
        *,
        group_id: int,
        user_id: int,
    ) -> bool:
        """Close an open group participation after membership is revoked.

        Group rows are always locked before voice rows so this operation remains
        safe both as a standalone command and when nested inside group services.
        Returning False means there was no active participation to revoke.
        """

        with transaction.atomic():
            group = (
                GroupConversation.objects
                .select_for_update()
                .filter(pk=group_id)
                .first()
            )

            if group is None:
                return False

            cls._lock_users(
                user_ids=[user_id],
            )

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.GROUP,
                    group=group,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                return False

            participation = (
                VoiceParticipation.objects
                .select_for_update()
                .filter(
                    session=session,
                    user_id=user_id,
                    left_at__isnull=True,
                )
                .first()
            )

            if participation is None:
                return False

            participation.left_at = timezone.now()
            participation.save(
                update_fields=["left_at"],
            )

            if not VoiceParticipation.objects.filter(
                session=session,
                left_at__isnull=True,
            ).exists():
                now = timezone.now()
                session.status = VoiceSession.Status.ENDED
                session.ended_at = now
                session.end_reason = VoiceSession.EndReason.EMPTY
                session.save(
                    update_fields=[
                        "status",
                        "ended_at",
                        "end_reason",
                    ]
                )
                VoiceMediaCleanup.delete_room_after_commit(
                    room_name=session.media_room_name,
                )
            else:
                VoiceMediaCleanup.remove_participant_after_commit(
                    room_name=session.media_room_name,
                    participant_identity=(
                        participation.media_participant_identity
                    ),
                )

            audience_user_ids = set(
                cls._group_member_user_ids(
                    group_id=group.pk,
                )
            )
            audience_user_ids.add(user_id)

            VoiceRealtimePublisher.group_participant_revoked_after_commit(
                session_id=session.pk,
                participation_id=participation.pk,
                group_id=group.pk,
                user_id=user_id,
                audience_user_ids=audience_user_ids,
                session_ended=(session.status == VoiceSession.Status.ENDED),
            )

            return True

    @classmethod
    def revoke_group_session(
        cls,
        *,
        group_id: int,
    ) -> bool:
        """Invalidate a whole active group voice room before group deletion."""

        with transaction.atomic():
            group = (
                GroupConversation.objects
                .select_for_update()
                .filter(pk=group_id)
                .first()
            )

            if group is None:
                return False

            session = (
                VoiceSession.objects
                .select_for_update()
                .filter(
                    kind=VoiceSession.Kind.GROUP,
                    group=group,
                    status=VoiceSession.Status.ACTIVE,
                )
                .first()
            )

            if session is None:
                return False

            audience_user_ids = cls._group_member_user_ids(
                group_id=group.pk,
            )

            cls._finish_session_locked(
                session=session,
                end_reason=VoiceSession.EndReason.ACCESS_REVOKED,
            )
            VoiceMediaCleanup.delete_room_after_commit(
                room_name=session.media_room_name,
            )

            VoiceRealtimePublisher.group_session_ended_after_commit(
                session_id=session.pk,
                group_id=group.pk,
                audience_user_ids=audience_user_ids,
                end_reason=session.end_reason,
                ended_at=session.ended_at,
            )

            return True
