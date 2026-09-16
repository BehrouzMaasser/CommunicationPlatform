from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from apps.conversations.models import GroupInvitation
from apps.friendships.models import FriendRequest
from apps.messaging.models import MessageReceipt
from apps.voice.models import VoiceRoomInvitation


User = get_user_model()


class ActivitySummarySelector:
    """
    Durable attention state for one user.

    This read model intentionally derives message unread state from
    MessageReceipt instead of duplicating it into a notifications table.
    Pending friend requests and group invitations are likewise read from
    their domain tables.
    """

    @staticmethod
    def _unread_direct_messages(*, user: User) -> list[dict]:
        rows = (
            MessageReceipt.objects
            .filter(
                user=user,
                read_at__isnull=True,
                message__direct_conversation__isnull=False,
            )
            .filter(
                Q(message__direct_conversation__user_1=user)
                | Q(message__direct_conversation__user_2=user)
            )
            .values(
                "message__direct_conversation_id",
            )
            .annotate(
                unread_count=Count("id"),
            )
            .order_by()
        )

        return [
            {
                "conversation_id": row[
                    "message__direct_conversation_id"
                ],
                "unread_count": row["unread_count"],
            }
            for row in rows
        ]

    @staticmethod
    def _unread_group_messages(*, user: User) -> list[dict]:
        # A former group member can still have historical receipt rows, but
        # cannot access that group anymore. Only current memberships belong
        # in the user's current unread/attention state.
        rows = (
            MessageReceipt.objects
            .filter(
                user=user,
                read_at__isnull=True,
                message__group_conversation__isnull=False,
                message__group_conversation__memberships__user=user,
            )
            .values(
                "message__group_conversation_id",
            )
            .annotate(
                unread_count=Count("id"),
            )
            .order_by()
        )

        return [
            {
                "group_id": row[
                    "message__group_conversation_id"
                ],
                "unread_count": row["unread_count"],
            }
            for row in rows
        ]

    @classmethod
    def get_for_user(cls, *, user: User) -> dict:
        direct_conversations = cls._unread_direct_messages(
            user=user,
        )
        groups = cls._unread_group_messages(
            user=user,
        )

        return {
            "pending_friend_requests": (
                FriendRequest.objects
                .filter(recipient=user)
                .count()
            ),
            "pending_group_invitations": (
                GroupInvitation.objects
                .filter(recipient=user)
                .count()
            ),
            "pending_voice_room_invitations": (
                VoiceRoomInvitation.objects
                .filter(recipient=user)
                .count()
            ),
            "unread_direct_messages": sum(
                item["unread_count"]
                for item in direct_conversations
            ),
            "unread_group_messages": sum(
                item["unread_count"]
                for item in groups
            ),
            "direct_conversations": direct_conversations,
            "groups": groups,
        }
