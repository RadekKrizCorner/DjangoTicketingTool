"""Django app configuration for audit."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configure the audit app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
