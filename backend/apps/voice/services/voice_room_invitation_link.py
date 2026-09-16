import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.db import transaction
from django.utils import timezone

from apps.voice.exceptions import (
    InvalidVoiceRoomInvitationLink,
    VoiceRoomInvitationLinkNotFound,
    VoiceRoomNotFound,
)
from apps.voice.models import (
    VoiceRoomInvitation,
    VoiceRoomInvitationLink,
    VoiceRoomMembership,
)
from apps.voice.room_realtime import (
    VoiceRoomRealtimePublisher,
)
from apps.voice.services.voice_room import VoiceRoomService


User = get_user_model()


class VoiceRoomInvitationLinkService:

    VALIDITY_PERIOD = timedelta(days=1)

    TOKEN_SIGNING_SALT = (
        "communication-platform."
        "voice-room-invitation-link"
    )

    @staticmethod
    def _hash_token(
        token: str,
    ) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _generate_placeholder_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def _signed_token_for_link_id(
        cls,
        *,
        link_id: UUID,
    ) -> str:
        signer = Signer(
            salt=cls.TOKEN_SIGNING_SALT,
        )

        return signer.sign(
            str(link_id),
        )

    @classmethod
    def recover_token(
        cls,
        *,
        link: VoiceRoomInvitationLink,
    ) -> str | None:
        token = cls._signed_token_for_link_id(
            link_id=link.pk,
        )

        if not secrets.compare_digest(
            link.token_hash,
            cls._hash_token(token),
        ):
            return None

        return token

    @classmethod
    def _get_link_room_id(
        cls,
        *,
        token_hash: str,
    ) -> UUID:
        try:
            return (
                VoiceRoomInvitationLink.objects
                .values_list(
                    "room_id",
                    flat=True,
                )
                .get(token_hash=token_hash)
            )
        except (
            VoiceRoomInvitationLink.DoesNotExist
        ) as exc:
            raise InvalidVoiceRoomInvitationLink from exc

    @classmethod
    def _get_link_for_update(
        cls,
        *,
        token_hash: str,
        room_id: UUID,
    ) -> VoiceRoomInvitationLink:
        try:
            return (
                VoiceRoomInvitationLink.objects
                .select_for_update(of=("self",))
                .get(
                    token_hash=token_hash,
                    room_id=room_id,
                )
            )
        except (
            VoiceRoomInvitationLink.DoesNotExist
        ) as exc:
            raise InvalidVoiceRoomInvitationLink from exc

    @classmethod
    def create_link(
        cls,
        *,
        current_user: User,
        room_id: UUID,
    ) -> tuple[
        VoiceRoomInvitationLink,
        str,
    ]:
        with transaction.atomic():
            room = VoiceRoomService._get_room_for_update(
                room_id=room_id,
            )

            VoiceRoomService._require_owner(
                room=room,
                user=current_user,
            )

            link = (
                VoiceRoomInvitationLink.objects.create(
                    room=room,
                    created_by=current_user,
                    token_hash=cls._hash_token(
                        cls._generate_placeholder_token()
                    ),
                    expires_at=(
                        timezone.now()
                        + cls.VALIDITY_PERIOD
                    ),
                )
            )

            token = cls._signed_token_for_link_id(
                link_id=link.pk,
            )

            link.token_hash = cls._hash_token(
                token,
            )

            link.save(
                update_fields=[
                    "token_hash",
                ],
            )

            (
                VoiceRoomRealtimePublisher
                .invite_link_created_after_commit(
                    link_id=link.pk,
                    room_id=room.pk,
                    owner_id=current_user.pk,
                    expires_at=link.expires_at,
                )
            )

        return link, token

    @classmethod
    def join_with_token(
        cls,
        *,
        current_user: User,
        token: str,
    ) -> tuple[
        VoiceRoomMembership,
        bool,
    ]:
        token_hash = cls._hash_token(
            token,
        )

        with transaction.atomic():
            room_id = cls._get_link_room_id(
                token_hash=token_hash,
            )

            try:
                room = (
                    VoiceRoomService
                    ._get_room_for_update(
                        room_id=room_id,
                    )
                )
            except VoiceRoomNotFound as exc:
                raise (
                    InvalidVoiceRoomInvitationLink
                ) from exc

            link = cls._get_link_for_update(
                token_hash=token_hash,
                room_id=room.pk,
            )

            now = timezone.now()

            if (
                link.revoked_at is not None
                or link.expires_at <= now
            ):
                raise InvalidVoiceRoomInvitationLink

            existing_membership = (
                VoiceRoomMembership.objects
                .filter(
                    room=room,
                    user=current_user,
                )
                .first()
            )

            if existing_membership is not None:
                return (
                    existing_membership,
                    False,
                )

            membership = (
                VoiceRoomMembership.objects.create(
                    room=room,
                    user=current_user,
                )
            )

            VoiceRoomInvitation.objects.filter(
                room=room,
                recipient=current_user,
            ).delete()

            (
                VoiceRoomRealtimePublisher
                .member_added_after_commit(
                    room_id=room.pk,
                    member_user_id=current_user.pk,
                    audience_user_ids=(
                        VoiceRoomService
                        ._member_user_ids(
                            room=room,
                        )
                    ),
                )
            )

        return membership, True

    @classmethod
    def revoke_link(
        cls,
        *,
        current_user: User,
        room_id: UUID,
        link_id: UUID,
    ) -> VoiceRoomInvitationLink:
        with transaction.atomic():
            room = VoiceRoomService._get_room_for_update(
                room_id=room_id,
            )

            VoiceRoomService._require_owner(
                room=room,
                user=current_user,
            )

            try:
                link = (
                    VoiceRoomInvitationLink.objects
                    .select_for_update(of=("self",))
                    .get(
                        pk=link_id,
                        room=room,
                    )
                )
            except (
                VoiceRoomInvitationLink.DoesNotExist
            ) as exc:
                raise (
                    VoiceRoomInvitationLinkNotFound
                ) from exc

            if link.revoked_at is None:
                link.revoked_at = timezone.now()

                link.save(
                    update_fields=[
                        "revoked_at",
                    ],
                )

                (
                    VoiceRoomRealtimePublisher
                    .invite_link_revoked_after_commit(
                        link_id=link.pk,
                        room_id=room.pk,
                        owner_id=current_user.pk,
                    )
                )

        return link
