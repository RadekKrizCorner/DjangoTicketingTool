"""Attachment models."""

from django.conf import settings
from django.db import models

from apps.common.models import AuditSoftDeleteModel


class Attachment(AuditSoftDeleteModel):
    """Represent a file attached to a task or comment."""

    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    comment = models.ForeignKey(
        "tasks.TaskComment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attachments",
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    checksum_sha256 = models.CharField(max_length=64)

    class Meta:
        """Configure attachment constraints and ordering."""

        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(task__isnull=False) & models.Q(comment__isnull=True))
                    | (models.Q(task__isnull=True) & models.Q(comment__isnull=False))
                ),
                name="attachments_exactly_one_parent",
            )
        ]

    def __str__(self) -> str:
        """Return the original filename."""
        return self.original_filename
