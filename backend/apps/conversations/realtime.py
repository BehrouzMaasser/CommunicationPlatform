from collections.abc import Iterable

from apps.realtime.events import RealtimeEventType
from apps.realtime.group_names import (
    conversation_group_name,
    user_group_name,
)
from apps.realtime.publisher import RealtimePublisher


class GroupRealtimePublisher:
    """
    Realtime adapter for committed group-domain outcomes.

    Group pages reconstruct canonical state through REST when an event arrives,
    so payloads contain stable identifiers/state hints rather than duplicating
    full DRF serializers.
    """

    @staticmethod
    def _audience_groups(
        *,
        group_id: int,
        user_ids: Iterable[int],
        include_conversation: bool = True,
    ) -> list[str]:
        group_names = [
            user_group_name(user_id)
            for user_id in set(user_ids)
        ]

        if include_conversation:
            group_names.append(
                conversation_group_name(
                    "group",
                    group_id,
                )
            )

        return group_names

    @classmethod
    def _publish_group_event_after_commit(
        cls,
        *,
        event_type: RealtimeEventType,
        payload: dict,
        group_id: int,
        user_ids: Iterable[int],
        include_conversation: bool = True,
    ) -> None:
        RealtimePublisher.publish_after_commit(
            event_type=event_type,
            payload=payload,
            group_names=cls._audience_groups(
                group_id=group_id,
                user_ids=user_ids,
                include_conversation=include_conversation,
            ),
        )

    @classmethod
    def invitation_created_after_commit(
        cls,
        *,
        invitation_id: int,
        group_id: int,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_INVITATION_CREATED,
            payload={
                "invitation_id": invitation_id,
                "group_id": group_id,
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
            group_id=group_id,
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            include_conversation=False,
        )

    @classmethod
    def invitation_accepted_after_commit(
        cls,
        *,
        invitation_id: int,
        group_id: int,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_INVITATION_ACCEPTED,
            payload={
                "invitation_id": invitation_id,
                "group_id": group_id,
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
            group_id=group_id,
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            include_conversation=False,
        )

    @classmethod
    def invitation_rejected_after_commit(
        cls,
        *,
        invitation_id: int,
        group_id: int,
        invited_by_id: int,
        recipient_id: int,
    ) -> None:
        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_INVITATION_REJECTED,
            payload={
                "invitation_id": invitation_id,
                "group_id": group_id,
                "invited_by_id": invited_by_id,
                "recipient_id": recipient_id,
            },
            group_id=group_id,
            user_ids=[
                invited_by_id,
                recipient_id,
            ],
            include_conversation=False,
        )

    @classmethod
    def member_added_after_commit(
        cls,
        *,
        group_id: int,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_MEMBER_ADDED,
            payload={
                "group_id": group_id,
                "user_id": member_user_id,
            },
            group_id=group_id,
            user_ids=audience_user_ids,
        )

    @classmethod
    def member_removed_after_commit(
        cls,
        *,
        group_id: int,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        audience = set(audience_user_ids)
        audience.add(member_user_id)

        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_MEMBER_REMOVED,
            payload={
                "group_id": group_id,
                "user_id": member_user_id,
            },
            group_id=group_id,
            user_ids=audience,
        )

        RealtimePublisher.force_unsubscribe_user_from_conversation_after_commit(
            user_id=member_user_id,
            conversation_type="group",
            conversation_id=group_id,
        )

    @classmethod
    def member_left_after_commit(
        cls,
        *,
        group_id: int,
        member_user_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        audience = set(audience_user_ids)
        audience.add(member_user_id)

        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_MEMBER_LEFT,
            payload={
                "group_id": group_id,
                "user_id": member_user_id,
            },
            group_id=group_id,
            user_ids=audience,
        )

        RealtimePublisher.force_unsubscribe_user_from_conversation_after_commit(
            user_id=member_user_id,
            conversation_type="group",
            conversation_id=group_id,
        )

    @classmethod
    def renamed_after_commit(
        cls,
        *,
        group_id: int,
        name: str,
        audience_user_ids: Iterable[int],
    ) -> None:
        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_RENAMED,
            payload={
                "group_id": group_id,
                "name": name,
            },
            group_id=group_id,
            user_ids=audience_user_ids,
        )

    @classmethod
    def deleted_after_commit(
        cls,
        *,
        group_id: int,
        audience_user_ids: Iterable[int],
    ) -> None:
        audience = set(audience_user_ids)

        cls._publish_group_event_after_commit(
            event_type=RealtimeEventType.GROUP_DELETED,
            payload={
                "group_id": group_id,
            },
            group_id=group_id,
            user_ids=audience,
        )

        for user_id in audience:
            RealtimePublisher.force_unsubscribe_user_from_conversation_after_commit(
                user_id=user_id,
                conversation_type="group",
                conversation_id=group_id,
            )
