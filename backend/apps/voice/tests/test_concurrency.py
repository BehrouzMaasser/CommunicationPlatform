import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.friendships.models import Friendship
from apps.voice.exceptions import VoiceParticipationClaimed, VoiceUserBusy
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


@skipUnless(
    connection.vendor == "postgresql",
    "Voice concurrency guarantees are verified against PostgreSQL row locks.",
)
class VoiceConcurrencyTests(TransactionTestCase):
    reset_sequences = True
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        realtime_patcher = patch(
            "apps.voice.realtime."
            "RealtimePublisher.publish_to_users_after_commit"
        )
        realtime_patcher.start()
        self.addCleanup(realtime_patcher.stop)

        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )
        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password=self.PASSWORD,
        )
        self.group = GroupConversation.objects.create(
            name="Voice Group",
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        user_1_id, user_2_id = sorted((self.alice.pk, self.bob.pk))
        Friendship.objects.create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )

    def test_two_devices_accepting_same_call_have_one_winner(self):
        session = VoiceSessionService.start_direct_call(
            current_user=self.alice,
            target_user_id=self.bob.pk,
            client_instance_id=uuid.uuid4(),
        )
        barrier = Barrier(2)

        def accept_from(client_instance_id):
            close_old_connections()
            try:
                bob = User.objects.get(pk=self.bob.pk)
                barrier.wait(timeout=5)
                try:
                    VoiceSessionService.accept_direct_call(
                        current_user=bob,
                        session_id=session.pk,
                        client_instance_id=client_instance_id,
                    )
                    return "accepted"
                except VoiceParticipationClaimed:
                    return "claimed"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    accept_from,
                    [uuid.uuid4(), uuid.uuid4()],
                )
            )

        self.assertCountEqual(
            results,
            ["accepted", "claimed"],
        )

    def test_group_join_and_direct_call_cannot_both_reserve_same_user(self):
        barrier = Barrier(2)

        def join_group():
            close_old_connections()
            try:
                alice = User.objects.get(pk=self.alice.pk)
                barrier.wait(timeout=5)
                try:
                    VoiceSessionService.join_group_voice(
                        current_user=alice,
                        group_id=self.group.pk,
                        client_instance_id=uuid.uuid4(),
                    )
                    return "joined"
                except VoiceUserBusy:
                    return "busy"
            finally:
                close_old_connections()

        def start_call():
            close_old_connections()
            try:
                alice = User.objects.get(pk=self.alice.pk)
                barrier.wait(timeout=5)
                try:
                    VoiceSessionService.start_direct_call(
                        current_user=alice,
                        target_user_id=self.bob.pk,
                        client_instance_id=uuid.uuid4(),
                    )
                    return "called"
                except VoiceUserBusy:
                    return "busy"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            group_future = executor.submit(join_group)
            call_future = executor.submit(start_call)
            results = [group_future.result(), call_future.result()]

        self.assertIn("busy", results)
        self.assertEqual(
            sum(result in {"joined", "called"} for result in results),
            1,
        )
