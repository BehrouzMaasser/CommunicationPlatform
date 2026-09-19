from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.realtime.ephemeral import (
    RealtimeEphemeralSelector,
)
from apps.realtime.presence import PresenceStore
from apps.voice.models import (
    VoiceRoom,
    VoiceRoomMembership,
)


User = get_user_model()


TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": (
            "channels.layers."
            "InMemoryChannelLayer"
        ),
    }
}


@override_settings(
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS,
)
class RealtimeEphemeralTests(TestCase):

    def setUp(self):
        PresenceStore._memory_leases.clear()

        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password-123",
        )
        self.charlie = User.objects.create_user(
            username="charlie",
            email="charlie@example.com",
            password="password-123",
        )
        self.dave = User.objects.create_user(
            username="dave",
            email="dave@example.com",
            password="password-123",
        )

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )

        self.friendship = (
            Friendship.objects.create(
                user_1=low,
                user_2=high,
            )
        )

        self.dm = (
            DirectConversation.objects.create(
                user_1=low,
                user_2=high,
            )
        )

        self.group = (
            GroupConversation.objects.create(
                name="Study Group",
            )
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=(
                GroupMembership.Role.OWNER
            ),
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=(
                GroupMembership.Role.MEMBER
            ),
        )

        self.voice_room = (
            VoiceRoom.objects.create(
                name="Voice Study",
                owner=self.alice,
            )
        )

        VoiceRoomMembership.objects.create(
            room=self.voice_room,
            user=self.alice,
        )

        VoiceRoomMembership.objects.create(
            room=self.voice_room,
            user=self.charlie,
        )

    def test_dm_typing_requires_active_friendship(self):
        self.assertTrue(
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.alice.pk,
                conversation_type="dm",
                conversation_id=self.dm.pk,
            )
        )

        self.friendship.delete()

        self.assertFalse(
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.alice.pk,
                conversation_type="dm",
                conversation_id=self.dm.pk,
            )
        )

    def test_dm_outsider_cannot_publish_typing(self):
        self.assertFalse(
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.charlie.pk,
                conversation_type="dm",
                conversation_id=self.dm.pk,
            )
        )

    def test_group_typing_requires_membership(self):
        self.assertTrue(
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.bob.pk,
                conversation_type="group",
                conversation_id=self.group.pk,
            )
        )

        GroupMembership.objects.filter(
            group=self.group,
            user=self.bob,
        ).delete()

        self.assertFalse(
            RealtimeEphemeralSelector
            .can_publish_typing(
                user_id=self.bob.pk,
                conversation_type="group",
                conversation_id=self.group.pk,
            )
        )

    def test_friend_audience_is_symmetric(self):
        self.assertEqual(
            set(
                RealtimeEphemeralSelector
                .friend_user_ids(
                    user_id=self.alice.pk,
                )
            ),
            {self.bob.pk},
        )

        self.assertEqual(
            set(
                RealtimeEphemeralSelector
                .friend_user_ids(
                    user_id=self.bob.pk,
                )
            ),
            {self.alice.pk},
        )

    def test_presence_audience_includes_shared_members(self):
        self.friendship.delete()

        self.assertEqual(
            set(
                RealtimeEphemeralSelector
                .presence_user_ids(
                    user_id=self.alice.pk,
                )
            ),
            {
                self.bob.pk,
                self.charlie.pk,
            },
        )

    def test_presence_audience_excludes_unrelated_users(self):
        self.assertNotIn(
            self.dave.pk,
            RealtimeEphemeralSelector
            .presence_user_ids(
                user_id=self.alice.pk,
            ),
        )

    def test_presence_is_multi_connection_safe(self):
        first_expiry = async_to_sync(
            PresenceStore.touch
        )(
            user_id=self.alice.pk,
            connection_id="tab-a",
        )

        second_expiry = async_to_sync(
            PresenceStore.touch
        )(
            user_id=self.alice.pk,
            connection_id="tab-b",
        )

        self.assertIsNotNone(
            first_expiry
        )
        self.assertIsNotNone(
            second_expiry
        )

        remaining = async_to_sync(
            PresenceStore.remove
        )(
            user_id=self.alice.pk,
            connection_id="tab-a",
        )

        self.assertIsNotNone(
            remaining
        )

        remaining = async_to_sync(
            PresenceStore.remove
        )(
            user_id=self.alice.pk,
            connection_id="tab-b",
        )

        self.assertIsNone(
            remaining
        )
