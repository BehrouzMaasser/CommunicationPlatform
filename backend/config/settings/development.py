import os

from .base import *


FRONTEND_BASE_URL = os.getenv(
    "DJANGO_FRONTEND_BASE_URL",
    "http://127.0.0.1:5173",
).rstrip("/")

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]