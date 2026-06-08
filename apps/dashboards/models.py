"""Dashboard domain models."""

from django.conf import settings
from django.db import models

from apps.common.models import AuditSoftDeleteModel


class Dashboard(AuditSoftDeleteModel):
    """Represent a configurable dashboard."""

    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_dashboards",
    )

    class Meta:
        """Configure dashboard ordering and indexes."""

        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["owner", "deleted_at"], name="dash_owner_active_idx"),
            models.Index(fields=["name", "deleted_at"], name="dash_name_active_idx"),
        ]

    def __str__(self) -> str:
        """Return the dashboard name."""
        return self.name


class DashboardWidget(AuditSoftDeleteModel):
    """Represent one widget on a dashboard."""

    class Type(models.TextChoices):
        """List supported dashboard widget types."""

        METRIC_TILE = "metric_tile", "Metric tile"
        STATUS_BREAKDOWN = "status_breakdown", "Status breakdown"
        PRIORITY_BREAKDOWN = "priority_breakdown", "Priority breakdown"
        TECHNICIAN_WORKLOAD = "technician_workload", "Technician workload"
        DUE_SOON_TABLE = "due_soon_table", "Due soon table"
        RECENT_ACTIVITY = "recent_activity", "Recent activity"

    dashboard = models.ForeignKey(Dashboard, on_delete=models.PROTECT, related_name="widgets")
    type = models.CharField(max_length=40, choices=Type.choices)
    title = models.CharField(max_length=200)
    config = models.JSONField(default=dict, blank=True)
    x = models.PositiveIntegerField(default=0)
    y = models.PositiveIntegerField(default=0)
    w = models.PositiveIntegerField(default=3)
    h = models.PositiveIntegerField(default=2)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        """Configure widget ordering and indexes."""

        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["dashboard", "deleted_at"], name="dash_widget_active_idx"),
            models.Index(fields=["dashboard", "order"], name="dash_widget_order_idx"),
        ]

    def __str__(self) -> str:
        """Return the widget title."""
        return self.title


class DashboardShare(AuditSoftDeleteModel):
    """Represent a dashboard sharing rule."""

    class TargetType(models.TextChoices):
        """List supported share target types."""

        USER = "user", "User"
        PROJECT_MEMBERS = "project_members", "Project members"

    class Access(models.TextChoices):
        """List supported share access levels."""

        VIEWER = "viewer", "Viewer"
        EDITOR = "editor", "Editor"

    dashboard = models.ForeignKey(Dashboard, on_delete=models.PROTECT, related_name="shares")
    target_type = models.CharField(max_length=30, choices=TargetType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dashboard_shares",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dashboard_shares",
    )
    access = models.CharField(max_length=20, choices=Access.choices, default=Access.VIEWER)

    class Meta:
        """Configure share ordering and indexes."""

        ordering = ["dashboard_id", "target_type", "id"]
        indexes = [
            models.Index(fields=["dashboard", "deleted_at"], name="dash_share_active_idx"),
            models.Index(fields=["user", "deleted_at"], name="dash_share_user_idx"),
            models.Index(fields=["project", "deleted_at"], name="dash_share_project_idx"),
        ]

    def __str__(self) -> str:
        """Return a readable share label."""
        target = self.user_id if self.target_type == self.TargetType.USER else self.project_id
        return f"{self.dashboard_id}:{self.target_type}:{target}:{self.access}"
