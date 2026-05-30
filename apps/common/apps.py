"""Django app configuration for common helpers."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Configure the common app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
