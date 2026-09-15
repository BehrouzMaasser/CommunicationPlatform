from django.core.management.base import BaseCommand, CommandError

from apps.voice.services.media_admin import LiveKitMediaAdminService


class Command(BaseCommand):
    help = "Verify authenticated server-to-server connectivity to LiveKit."

    def handle(self, *args, **options):
        try:
            response = LiveKitMediaAdminService.list_rooms()
        except Exception as exc:
            raise CommandError(
                f"LiveKit media check failed: {exc}"
            ) from exc

        rooms = getattr(response, "rooms", ())
        self.stdout.write(
            self.style.SUCCESS(
                f"LiveKit media check passed ({len(rooms)} active rooms)."
            )
        )
