"""Audit log models."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Record a domain action for audit history."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.BigIntegerField()
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configure audit log ordering, indexes, and constraints."""

        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "-created_at"], name="audit_log_project_created_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="audit_log_entity_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="audit_log_idempotency_key_uniq",
            )
        ]

    def __str__(self) -> str:
        """Return a readable audit log label."""
        return f"{self.action} {self.entity_type}:{self.entity_id}"
