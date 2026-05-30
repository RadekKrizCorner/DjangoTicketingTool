"""Test suite Django settings."""

import dj_database_url
from decouple import config

from .base import *  # noqa: F403
from .base import MIDDLEWARE as BASE_MIDDLEWARE

SECRET_KEY = "test-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "api"]
TEST_DATABASE_URL = config(
    "TEST_DATABASE_URL",
    default=config("DATABASE_URL", default="postgres://app:app@localhost:5432/app"),
)
DATABASES = {
    "default": dj_database_url.parse(TEST_DATABASE_URL, conn_max_age=0),
}
DATABASES["default"]["TEST"] = {"NAME": "test_app"}
MIDDLEWARE = [
    middleware
    for middleware in BASE_MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
