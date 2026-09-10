from django.contrib.auth import get_user_model
from django.db import transaction

from apps.conversations.exceptions import (
    DirectConversationTargetNotFound,
    FriendshipRequiredForDirectConversation,
    SelfDirectConversationNotAllowed,
)
from apps.conversations.models import DirectConversation
from apps.friendships.models import Friendship


User = get_user_model()


class DirectConversationService:

    @staticmethod
    def _canonical_user_ids(
        *,
        user_a: User,
        user_b: User,
    ) -> tuple[int, int]:
        if user_a.pk == user_b.pk:
            raise SelfDirectConversationNotAllowed

        return sorted([user_a.pk, user_b.pk])

    @classmethod
    def get_or_create(
        cls,
        *,
        current_user: User,
        target_user_id: int,
    ) -> tuple[DirectConversation, bool]:
        try:
            target_user = User.objects.get(
                pk=target_user_id,
            )
        except User.DoesNotExist as exc:
            raise DirectConversationTargetNotFound from exc

        user_1_id, user_2_id = cls._canonical_user_ids(
            user_a=current_user,
            user_b=target_user,
        )

        with transaction.atomic():
            existing_conversation = (
                DirectConversation.objects
                .filter(
                    user_1_id=user_1_id,
                    user_2_id=user_2_id,
                )
                .first()
            )

            if existing_conversation is not None:
                return existing_conversation, False

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
                raise FriendshipRequiredForDirectConversation

            conversation, created = (
                DirectConversation.objects.get_or_create(
                    user_1_id=user_1_id,
                    user_2_id=user_2_id,
                )
            )

            # Later, if created:
            #
            # transaction.on_commit(
            #     lambda: publish DirectConversationCreated(...)
            # )

        return conversation, created
