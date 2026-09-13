from .base import *

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

FRONTEND_BASE_URL = os.getenv(
    "DJANGO_FRONTEND_BASE_URL",
    "http://127.0.0.1:5173",
).rstrip("/")

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"

if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
