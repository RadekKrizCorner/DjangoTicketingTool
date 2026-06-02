"""Observability Django app configuration."""

from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    """Configure observability integration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.observability"
