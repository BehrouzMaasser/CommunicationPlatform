from django.apps import AppConfig


class VoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.voice"

    def ready(self):
        from apps.voice import signals  # noqa: F401
