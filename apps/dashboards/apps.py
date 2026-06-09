"""Dashboard app configuration."""

from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    """Configure the dashboards app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboards"
