"""Notification and email delivery models."""

from django.conf import settings
from django.db import models

from apps.common.models import AuditSoftDeleteModel


class Notification(AuditSoftDeleteModel):
    """Represent an in-app notification."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    type = models.CharField(max_length=80)
    title = models.CharField(max_length=200)
    message = models.TextField()
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    dedupe_key = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Configure notification ordering and uniqueness."""

        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                name="notifications_user_dedupe_unique",
            )
        ]

    def __str__(self) -> str:
        """Return a readable notification label."""
        return f"{self.type}:{self.user_id}"


class EmailDelivery(models.Model):
    """Represent an email delivery outbox row."""

    class Status(models.TextChoices):
        """List email delivery status choices."""

        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_deliveries",
    )
    notification = models.ForeignKey(
        Notification,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="email_deliveries",
    )
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Configure email delivery ordering and uniqueness."""

        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"],
                name="notifications_email_delivery_notification_user_unique",
            )
        ]

    def __str__(self) -> str:
        """Return a readable email delivery label."""
        return f"{self.email}:{self.status}"
