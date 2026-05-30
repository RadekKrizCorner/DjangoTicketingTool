"""Django app configuration for health checks."""

from django.apps import AppConfig


class HealthConfig(AppConfig):
    """Configure the health app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.health"
