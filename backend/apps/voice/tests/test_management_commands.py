from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class VoiceManagementCommandTests(SimpleTestCase):
    @patch(
        "apps.voice.management.commands.check_voice_media."
        "LiveKitMediaAdminService.list_rooms"
    )
    def test_check_voice_media_reports_authenticated_probe(self, list_rooms):
        list_rooms.return_value = Mock(rooms=[Mock(), Mock()])
        output = StringIO()

        call_command("check_voice_media", stdout=output)

        self.assertIn(
            "LiveKit media check passed (2 active rooms).",
            output.getvalue(),
        )
