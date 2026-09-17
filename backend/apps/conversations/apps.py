from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    name = 'apps.conversations'

    def ready(self):
        from apps.conversations import signals  # noqa: F401
