"""Django app configuration for shared API helpers."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Configure the shared API app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
