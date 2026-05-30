"""Django app configuration for attachments."""

from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    """Configure the attachments app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attachments"
