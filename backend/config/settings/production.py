import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403,F401


def _required_env(name):
    value = os.getenv(name)
    if not value or value.strip() in {"", "change-me"}:
        raise ImproperlyConfigured(
            f"Required production environment variable {name} is missing or unsafe."
        )
    return value.strip()


def _csv_env(name):
    return [
        item.strip()
        for item in os.getenv(name, "").split(",")
        if item.strip()
    ]


def _bool_env(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = False
SECRET_KEY = _required_env("DJANGO_SECRET_KEY")
FRONTEND_BASE_URL = os.getenv(
    "DJANGO_FRONTEND_BASE_URL",
    "",
).rstrip("/")

ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain explicit production hosts and may not use '*'."
    )

CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = _csv_env("DJANGO_CORS_ALLOWED_ORIGINS")

DATABASES["default"].update(  # noqa: F405
    {
        "NAME": _required_env("POSTGRES_DB"),
        "USER": _required_env("POSTGRES_USER"),
        "PASSWORD": _required_env("POSTGRES_PASSWORD"),
        "HOST": _required_env("POSTGRES_HOST"),
        "PORT": _required_env("POSTGRES_PORT"),
        # Persistent Django DB connections are disabled under ASGI.
        # Add an external pooler later if connection pooling is needed.
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "0")),
        "CONN_HEALTH_CHECKS": True,
    }
)

REDIS_URL = _required_env("REDIS_URL")
CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [REDIS_URL]  # noqa: F405

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
MEDIA_ROOT = Path(  # noqa: F405
    os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))  # noqa: F405
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _bool_env("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# The application does not currently send email, but production must not use
# Django's development-only console backend. Keep SMTP pointed at localhost by
# default so accidental sends fail locally and quickly until a real provider is
# configured.
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": os.getenv("DJANGO_EMAIL_HOST", "127.0.0.1"),
            "port": int(os.getenv("DJANGO_EMAIL_PORT", "25")),
            "username": os.getenv("DJANGO_EMAIL_HOST_USER") or None,
            "password": os.getenv("DJANGO_EMAIL_HOST_PASSWORD") or None,
            "use_tls": _bool_env("DJANGO_EMAIL_USE_TLS", False),
            "use_ssl": _bool_env("DJANGO_EMAIL_USE_SSL", False),
            "timeout": int(os.getenv("DJANGO_EMAIL_TIMEOUT", "10")),
        },
    },
}
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "webmaster@localhost")
SERVER_EMAIL = os.getenv("DJANGO_SERVER_EMAIL", "root@localhost")

# Start HSTS at 0 while the first HTTPS deployment is being verified.
# Raise this deliberately after HTTPS is confirmed stable.
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _bool_env(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    False,
)
SECURE_HSTS_PRELOAD = _bool_env("DJANGO_SECURE_HSTS_PRELOAD", False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
}
