from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.voice.services.media_cleanup import VoiceMediaCleanup


class VoiceMediaCleanupTests(SimpleTestCase):
    @override_settings(VOICE_ENABLED=False)
    @patch(
        "apps.voice.services.media_cleanup."
        "LiveKitMediaAdminService.delete_room"
    )
    @patch("apps.voice.services.media_cleanup.transaction.on_commit")
    def test_cleanup_is_noop_when_voice_disabled(
        self,
        on_commit,
        delete_room,
    ):
        on_commit.side_effect = lambda callback: callback()

        VoiceMediaCleanup.delete_room_after_commit(room_name="room")

        delete_room.assert_not_called()

    @override_settings(VOICE_ENABLED=True)
    @patch(
        "apps.voice.services.media_cleanup."
        "LiveKitMediaAdminService.remove_participant",
        side_effect=RuntimeError("media server unavailable"),
    )
    @patch("apps.voice.services.media_cleanup.transaction.on_commit")
    def test_cleanup_failure_does_not_escape_committed_domain_action(
        self,
        on_commit,
        remove_participant,
    ):
        on_commit.side_effect = lambda callback: callback()

        VoiceMediaCleanup.remove_participant_after_commit(
            room_name="room",
            participant_identity="participant",
        )

        remove_participant.assert_called_once_with(
            room_name="room",
            participant_identity="participant",
        )
