"""Task domain models."""

from django.conf import settings
from django.db import models

from apps.common.models import AuditSoftDeleteModel


class Task(AuditSoftDeleteModel):
    """Represent a project task."""

    class Status(models.TextChoices):
        """List task workflow status choices."""

        NEW = "new", "New"
        ACCEPTED = "accepted", "Accepted"
        IN_PROGRESS = "in_progress", "In progress"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        """List task priority choices."""

        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Configure task ordering."""

        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["project", "status", "due_at"],
                name="tasks_project_status_due_idx",
            ),
            models.Index(
                fields=["project", "assignee", "due_at"],
                name="tasks_project_assignee_due_idx",
            ),
            models.Index(
                fields=["project", "priority", "-created_at"],
                name="tasks_project_priority_idx",
            ),
        ]

    def __str__(self) -> str:
        """Return the task title."""
        return self.title


class TaskComment(AuditSoftDeleteModel):
    """Represent a comment on a task."""

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_comments",
    )
    body = models.TextField()

    class Meta:
        """Configure comment ordering."""

        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        """Return a readable comment label."""
        return f"Comment {self.id} on task {self.task_id}"


class TaskWatcher(AuditSoftDeleteModel):
    """Represent a user's task watcher subscription."""

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="watchers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_watchers",
    )

    class Meta:
        """Configure watcher ordering and active uniqueness."""

        ordering = ["task_id", "user_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="tasks_active_watcher_task_user_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["task", "deleted_at"], name="tasks_watcher_task_active_idx"),
            models.Index(fields=["user", "deleted_at"], name="tasks_watcher_user_active_idx"),
        ]

    def __str__(self) -> str:
        """Return a readable watcher label."""
        return f"{self.task_id}:{self.user_id}"
