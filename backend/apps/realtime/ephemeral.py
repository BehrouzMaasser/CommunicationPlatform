from django.db.models import Q

from apps.conversations.models import (
    DirectConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.voice.models import VoiceRoomMembership


class RealtimeEphemeralSelector:
    """
    Read-only authorization/audience rules for ephemeral realtime state.
    """

    @staticmethod
    def friend_user_ids(
        *,
        user_id: int,
    ) -> list[int]:
        pairs = list(
            Friendship.objects
            .filter(
                Q(user_1_id=user_id)
                | Q(user_2_id=user_id)
            )
            .values_list(
                "user_1_id",
                "user_2_id",
            )
        )

        return [
            user_2_id
            if user_1_id == user_id
            else user_1_id
            for user_1_id, user_2_id
            in pairs
        ]

    @staticmethod
    def presence_user_ids(
        *,
        user_id: int,
    ) -> list[int]:
        """
        Users whose ephemeral online/offline state may be shared with the
        current user. Presence is visible across an accepted friendship, a
        shared Group Chat, or a shared Voice Room membership.
        """

        visible_user_ids = set(
            RealtimeEphemeralSelector
            .friend_user_ids(
                user_id=user_id,
            )
        )

        group_ids = (
            GroupMembership.objects
            .filter(user_id=user_id)
            .values_list(
                "group_id",
                flat=True,
            )
        )

        visible_user_ids.update(
            GroupMembership.objects
            .filter(group_id__in=group_ids)
            .exclude(user_id=user_id)
            .values_list(
                "user_id",
                flat=True,
            )
        )

        voice_room_ids = (
            VoiceRoomMembership.objects
            .filter(user_id=user_id)
            .values_list(
                "room_id",
                flat=True,
            )
        )

        visible_user_ids.update(
            VoiceRoomMembership.objects
            .filter(room_id__in=voice_room_ids)
            .exclude(user_id=user_id)
            .values_list(
                "user_id",
                flat=True,
            )
        )

        return sorted(visible_user_ids)

    @staticmethod
    def can_publish_typing(
        *,
        user_id: int,
        conversation_type: str,
        conversation_id: int,
    ) -> bool:
        if conversation_type == "dm":
            conversation = (
                DirectConversation.objects
                .filter(pk=conversation_id)
                .filter(
                    Q(user_1_id=user_id)
                    | Q(user_2_id=user_id)
                )
                .first()
            )

            if conversation is None:
                return False

            other_user_id = (
                conversation.user_2_id
                if
                conversation.user_1_id
                == user_id
                else
                conversation.user_1_id
            )

            return Friendship.objects.filter(
                Q(
                    user_1_id=user_id,
                    user_2_id=other_user_id,
                )
                | Q(
                    user_1_id=other_user_id,
                    user_2_id=user_id,
                )
            ).exists()

        if conversation_type == "group":
            return (
                GroupMembership.objects
                .filter(
                    group_id=conversation_id,
                    user_id=user_id,
                )
                .exists()
            )

        return False
