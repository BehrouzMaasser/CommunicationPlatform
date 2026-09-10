from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    name = "apps.attachments"

    def ready(self):
        # Register storage-cleanup signal handlers.
        from apps.attachments import signals  # noqa: F401
