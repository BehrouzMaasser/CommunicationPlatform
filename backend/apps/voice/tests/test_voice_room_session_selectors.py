import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.voice.models import (
    VoiceRoomMembership,
)
from apps.voice.selectors.voice_session import (
    VoiceSessionSelector,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)
from apps.voice.services.voice_session import (
    VoiceSessionService,
)


User = get_user_model()


class VoiceRoomSessionSelectorTests(TestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.alice = User.objects.create_user(
            username="room-selector-alice",
            email="room-selector-alice@example.com",
            password=self.PASSWORD,
        )

        self.bob = User.objects.create_user(
            username="room-selector-bob",
            email="room-selector-bob@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.alice,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.bob,
        )

    def test_get_active_room_session(self):
        participation = (
            VoiceSessionService.join_voice_room(
                current_user=self.alice,
                room_id=self.room.id,
                client_instance_id=uuid.uuid4(),
            )
        )

        selected = (
            VoiceSessionSelector
            .get_active_room_session(
                room_id=self.room.id,
            )
        )

        self.assertEqual(
            selected.pk,
            participation.session_id,
        )

    def test_open_room_participations_exclude_left_user(
        self,
    ):
        alice_client = uuid.uuid4()

        VoiceSessionService.join_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=alice_client,
        )

        bob = (
            VoiceSessionService.join_voice_room(
                current_user=self.bob,
                room_id=self.room.id,
                client_instance_id=uuid.uuid4(),
            )
        )

        VoiceSessionService.leave_voice_room(
            current_user=self.alice,
            room_id=self.room.id,
            client_instance_id=alice_client,
        )

        open_participations = list(
            VoiceSessionSelector
            .list_open_room_participations(
                room_id=self.room.id,
            )
        )

        self.assertEqual(
            [
                participation.pk
                for participation
                in open_participations
            ],
            [
                bob.pk,
            ],
        )
