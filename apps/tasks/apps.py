"""Django app configuration for tasks."""

from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Configure the tasks app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
