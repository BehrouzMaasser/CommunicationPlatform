import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.models import GroupConversation, GroupMembership
from apps.voice.selectors.voice_session import VoiceSessionSelector
from apps.voice.services.voice_session import VoiceSessionService


User = get_user_model()


class VoiceSessionSelectorTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
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
        self.group = GroupConversation.objects.create(name="Voice Group")
        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=GroupMembership.Role.OWNER,
        )
        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=GroupMembership.Role.MEMBER,
        )

    def test_get_open_participation_for_user(self):
        participation = VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=self.group.pk,
            client_instance_id=uuid.uuid4(),
        )

        selected = VoiceSessionSelector.get_open_participation_for_user(
            user=self.alice,
        )

        self.assertEqual(selected.pk, participation.pk)

    def test_list_open_group_participations_excludes_left_users(self):
        alice_client = uuid.uuid4()
        VoiceSessionService.join_group_voice(
            current_user=self.alice,
            group_id=self.group.pk,
            client_instance_id=alice_client,
        )
        bob_participation = VoiceSessionService.join_group_voice(
            current_user=self.bob,
            group_id=self.group.pk,
            client_instance_id=uuid.uuid4(),
        )

        VoiceSessionService.leave_group_voice(
            current_user=self.alice,
            group_id=self.group.pk,
            client_instance_id=alice_client,
        )

        open_participations = list(
            VoiceSessionSelector.list_open_group_participations(
                group_id=self.group.pk,
            )
        )

        self.assertEqual(
            [participation.pk for participation in open_participations],
            [bob_participation.pk],
        )
