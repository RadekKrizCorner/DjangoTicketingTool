"""Base Django settings shared by all environments."""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-local-secret")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,testserver",
    cast=Csv(),
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts",
    "apps.api",
    "apps.attachments",
    "apps.audit",
    "apps.common",
    "apps.health",
    "apps.notifications",
    "apps.projects",
    "apps.tasks",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://app:app@db:5432/app",
        conn_max_age=60,
    )
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "EXCEPTION_HANDLER": "apps.api.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "password_reset": "3/min",
        "upload": "20/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Project Management API",
    "DESCRIPTION": "Django/DRF project management backend API.",
    "VERSION": "1.0.0",
}

CORS_ALLOWED_ORIGINS = config(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default="",
    cast=Csv(),
)

REDIS_URL = config("REDIS_URL", default="redis://redis:6379/0")
HEALTH_REDIS_URL = config("HEALTH_REDIS_URL", default="")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "publish-due-projects": {
        "task": "apps.notifications.tasks.publish_due_projects",
        "schedule": 60.0,
    },
    "close-due-projects": {
        "task": "apps.notifications.tasks.close_due_projects",
        "schedule": 60.0,
    },
    "send-deadline-reminders": {
        "task": "apps.notifications.tasks.send_deadline_reminders",
        "schedule": 900.0,
    },
    "send-pending-emails": {
        "task": "apps.notifications.tasks.send_pending_emails",
        "schedule": 60.0,
    },
}

EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@example.test")
PUBLIC_DOCUMENTATION_URL = config(
    "PUBLIC_DOCUMENTATION_URL",
    default="http://localhost:8001/",
)

ATTACHMENT_MAX_FILE_SIZE_BYTES = config(
    "ATTACHMENT_MAX_FILE_SIZE_BYTES",
    default=1_048_576,
    cast=int,
)
ATTACHMENT_MAX_TOTAL_BYTES = config(
    "ATTACHMENT_MAX_TOTAL_BYTES",
    default=209_715_200,
    cast=int,
)
ATTACHMENT_MAX_PROJECT_BYTES = config(
    "ATTACHMENT_MAX_PROJECT_BYTES",
    default=20_971_520,
    cast=int,
)
DATA_UPLOAD_MAX_MEMORY_SIZE = ATTACHMENT_MAX_FILE_SIZE_BYTES + 131_072
FILE_UPLOAD_MAX_MEMORY_SIZE = ATTACHMENT_MAX_FILE_SIZE_BYTES
