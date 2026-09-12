import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.conversations.exceptions import (
    GroupInvitationLinkNotFound,
    InvalidGroupInvitationLink,
)
from apps.conversations.models import (
    GroupConversation,
    GroupInvitation,
    GroupInvitationLink,
    GroupMembership,
)
from apps.conversations.services.group_conversation import (
    GroupConversationService,
)
from apps.conversations.realtime import GroupRealtimePublisher


User = get_user_model()


class GroupInvitationLinkService:
    VALIDITY_PERIOD = timedelta(days=1)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create_link(
        cls,
        *,
        current_user: User,
        group_id: int,
    ) -> tuple[GroupInvitationLink, str]:
        with transaction.atomic():
            group = GroupConversationService._get_group_for_update(
                group_id=group_id,
            )

            GroupConversationService._require_owner(
                group=group,
                user=current_user,
            )

            token = cls._generate_token()

            link = GroupInvitationLink.objects.create(
                group=group,
                created_by=current_user,
                token_hash=cls._hash_token(token),
                expires_at=(
                    timezone.now()
                    + cls.VALIDITY_PERIOD
                ),
            )

        return link, token

    @classmethod
    def join_with_token(
        cls,
        *,
        current_user: User,
        token: str,
    ) -> tuple[GroupMembership, bool]:
        token_hash = cls._hash_token(token)

        with transaction.atomic():
            try:
                link = (
                    GroupInvitationLink.objects
                    .select_for_update()
                    .select_related("group")
                    .get(token_hash=token_hash)
                )
            except GroupInvitationLink.DoesNotExist as exc:
                raise InvalidGroupInvitationLink from exc

            group = (
                GroupConversation.objects
                .select_for_update()
                .get(pk=link.group_id)
            )

            now = timezone.now()

            if (
                link.revoked_at is not None
                or link.expires_at <= now
            ):
                raise InvalidGroupInvitationLink

            existing_membership = (
                GroupMembership.objects
                .filter(
                    group=group,
                    user=current_user,
                )
                .first()
            )

            if existing_membership is not None:
                return existing_membership, False

            membership = GroupConversationService._add_member(
                group=group,
                user=current_user,
            )

            # A successful link join supersedes any direct pending
            # invitation for the same user/group.
            GroupInvitation.objects.filter(
                group=group,
                recipient=current_user,
            ).delete()

            audience_user_ids = list(
                GroupMembership.objects
                .filter(group=group)
                .values_list(
                    "user_id",
                    flat=True,
                )
            )

            GroupRealtimePublisher.member_added_after_commit(
                group_id=group.pk,
                member_user_id=current_user.pk,
                audience_user_ids=audience_user_ids,
            )

        return membership, True

    @classmethod
    def revoke_link(
        cls,
        *,
        current_user: User,
        group_id: int,
        link_id: int,
    ) -> GroupInvitationLink:
        with transaction.atomic():
            group = GroupConversationService._get_group_for_update(
                group_id=group_id,
            )

            GroupConversationService._require_owner(
                group=group,
                user=current_user,
            )

            try:
                link = (
                    GroupInvitationLink.objects
                    .select_for_update()
                    .get(
                        pk=link_id,
                        group=group,
                    )
                )
            except GroupInvitationLink.DoesNotExist as exc:
                raise GroupInvitationLinkNotFound from exc

            if link.revoked_at is None:
                link.revoked_at = timezone.now()
                link.save(
                    update_fields=["revoked_at"],
                )

        return link
