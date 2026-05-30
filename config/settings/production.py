"""Production Django settings."""

from decouple import Csv, config

from config.settings.base import *  # noqa: F403

DEBUG = False
SECRET_KEY = config("DJANGO_SECRET_KEY")
HEALTHCHECK_HOST = config("DJANGO_HEALTHCHECK_HOST", default="localhost")
ALLOWED_HOSTS = [
    *config("DJANGO_ALLOWED_HOSTS", cast=Csv()),
    HEALTHCHECK_HOST,
]
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_REDIRECT_EXEMPT = [
    r"^api/v1/health/live/$",
    r"^api/v1/health/ready/$",
]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
