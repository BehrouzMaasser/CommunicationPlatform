import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.realtime.events import RealtimeEventType
from apps.voice.room_realtime import (
    VoiceRoomRealtimePublisher,
)


class VoiceRoomRealtimePublisherTests(
    SimpleTestCase
):

    @patch(
        "apps.voice.room_realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_room_rename_event(
        self,
        publish,
    ):
        room_id = uuid.uuid4()

        (
            VoiceRoomRealtimePublisher
            .room_renamed_after_commit(
                room_id=room_id,
                room_name="Gaming",
                audience_user_ids=[1, 2],
            )
        )

        publish.assert_called_once_with(
            user_ids=[1, 2],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_RENAMED
            ),
            payload={
                "room_id": str(room_id),
                "room_name": "Gaming",
            },
        )

    @patch(
        "apps.voice.room_realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_member_added_event(
        self,
        publish,
    ):
        room_id = uuid.uuid4()

        (
            VoiceRoomRealtimePublisher
            .member_added_after_commit(
                room_id=room_id,
                member_user_id=3,
                audience_user_ids=[1, 2, 3],
            )
        )

        publish.assert_called_once_with(
            user_ids=[1, 2, 3],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_MEMBER_ADDED
            ),
            payload={
                "room_id": str(room_id),
                "member_user_id": 3,
            },
        )

    @patch(
        "apps.voice.room_realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_invitation_created_event(
        self,
        publish,
    ):
        room_id = uuid.uuid4()
        invitation_id = uuid.uuid4()

        (
            VoiceRoomRealtimePublisher
            .invitation_created_after_commit(
                invitation_id=invitation_id,
                room_id=room_id,
                room_name="Gaming",
                invited_by_id=1,
                recipient_id=2,
            )
        )

        publish.assert_called_once_with(
            user_ids=[1, 2],
            event_type=(
                RealtimeEventType
                .VOICE_ROOM_INVITATION_CREATED
            ),
            payload={
                "invitation_id": str(
                    invitation_id
                ),
                "room_id": str(room_id),
                "room_name": "Gaming",
                "invited_by_id": 1,
                "recipient_id": 2,
            },
        )

    @patch(
        "apps.voice.room_realtime."
        "RealtimePublisher."
        "publish_to_users_after_commit"
    )
    def test_invite_link_event_does_not_publish_token(
        self,
        publish,
    ):
        room_id = uuid.uuid4()
        link_id = uuid.uuid4()
        expires_at = (
            timezone.now()
            + timedelta(days=1)
        )

        (
            VoiceRoomRealtimePublisher
            .invite_link_created_after_commit(
                link_id=link_id,
                room_id=room_id,
                owner_id=1,
                expires_at=expires_at,
            )
        )

        kwargs = publish.call_args.kwargs

        self.assertEqual(
            kwargs["user_ids"],
            [1],
        )

        self.assertEqual(
            kwargs["event_type"],
            (
                RealtimeEventType
                .VOICE_ROOM_INVITE_LINK_CREATED
            ),
        )

        self.assertNotIn(
            "token",
            kwargs["payload"],
        )

        self.assertEqual(
            kwargs["payload"]["link_id"],
            str(link_id),
        )
