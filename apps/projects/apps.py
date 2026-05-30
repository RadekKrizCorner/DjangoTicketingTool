"""Django app configuration for projects."""

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Configure the projects app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
