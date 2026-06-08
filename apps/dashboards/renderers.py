"""Dashboard widget renderers."""

from typing import Any

from django.db.models import Count, Min, QuerySet
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.dashboards.models import Dashboard, DashboardWidget
from apps.projects import selectors as project_selectors
from apps.tasks.models import Task

OPEN_STATUSES = [
    Task.Status.NEW,
    Task.Status.ACCEPTED,
    Task.Status.IN_PROGRESS,
    Task.Status.ON_HOLD,
]
TASK_FILTER_KEYS = {"project_ids", "statuses", "priorities", "assignee_ids", "due_window"}


def render_dashboard(*, dashboard: Dashboard, user: Any, filters: dict | None = None) -> dict:
    """Render a dashboard for a user."""
    temporary_filters = filters or {}
    widgets = dashboard.widgets.filter(deleted_at__isnull=True).order_by("order", "id")
    return {
        "dashboard_id": dashboard.id,
        "widgets": [
            render_widget(widget=widget, user=user, temporary_filters=temporary_filters)
            for widget in widgets
        ],
    }


def render_widget(*, widget: DashboardWidget, user: Any, temporary_filters: dict) -> dict:
    """Render one dashboard widget."""
    effective_filters = effective_task_filters(
        config=widget.config,
        temporary_filters=temporary_filters,
    )
    tasks = filtered_tasks_for_user(user=user, filters=effective_filters)
    if widget.type == DashboardWidget.Type.METRIC_TILE:
        result = {"value": tasks.count()}
        drilldown = task_list_drilldown(filters=effective_filters)
    elif widget.type == DashboardWidget.Type.STATUS_BREAKDOWN:
        result = {"items": grouped_counts(tasks=tasks, field="status")}
        drilldown = task_list_drilldown(filters=effective_filters)
    elif widget.type == DashboardWidget.Type.PRIORITY_BREAKDOWN:
        result = {"items": grouped_counts(tasks=tasks, field="priority")}
        drilldown = task_list_drilldown(filters=effective_filters)
    elif widget.type == DashboardWidget.Type.TECHNICIAN_WORKLOAD:
        result = {"rows": technician_rows(tasks=tasks)}
        drilldown = task_list_drilldown(filters=effective_filters)
    elif widget.type == DashboardWidget.Type.DUE_SOON_TABLE:
        result = {"rows": task_rows(tasks=tasks)}
        drilldown = task_list_drilldown(filters=effective_filters)
    elif widget.type == DashboardWidget.Type.RECENT_ACTIVITY:
        result = {"items": recent_activity_items(user=user, filters=effective_filters)}
        drilldown = {"type": "activity"}
    else:
        result = {}
        drilldown = task_list_drilldown(filters=effective_filters)
    return {
        "id": widget.id,
        "type": widget.type,
        "title": widget.title,
        "config": widget.config,
        "layout": {
            "x": widget.x,
            "y": widget.y,
            "w": widget.w,
            "h": widget.h,
            "order": widget.order,
        },
        "result": result,
        "drilldown": drilldown,
    }


def filtered_tasks_for_user(*, user: Any, filters: dict) -> QuerySet[Task]:
    """Return tasks visible to a user with widget filters applied."""
    visible_project_ids = list(
        project_selectors.visible_projects_for_user(user).values_list("id", flat=True)
    )
    tasks = Task.objects.filter(
        deleted_at__isnull=True,
        project__deleted_at__isnull=True,
        project_id__in=visible_project_ids,
    ).select_related("project", "assignee")
    project_ids = filters.get("project_ids") or []
    if project_ids:
        tasks = tasks.filter(project_id__in=project_ids)
    statuses = filters.get("statuses") or []
    if statuses:
        tasks = tasks.filter(status__in=statuses)
    priorities = filters.get("priorities") or []
    if priorities:
        tasks = tasks.filter(priority__in=priorities)
    assignee_ids = filters.get("assignee_ids") or []
    if assignee_ids:
        tasks = tasks.filter(assignee_id__in=assignee_ids)
    due_window = filters.get("due_window")
    if due_window:
        tasks = apply_due_window(tasks=tasks, due_window=due_window)
    return tasks


def effective_task_filters(*, config: dict, temporary_filters: dict) -> dict:
    """Merge widget config filters with temporary dashboard filters."""
    filters = {
        key: config[key]
        for key in TASK_FILTER_KEYS
        if key in config and config[key] not in (None, "", [], "all")
    }
    for key in TASK_FILTER_KEYS:
        value = temporary_filters.get(key)
        if value not in (None, "", [], "all"):
            filters[key] = value
    return filters


def apply_due_window(*, tasks: QuerySet[Task], due_window: str) -> QuerySet[Task]:
    """Apply a relative due-date window to tasks."""
    now = timezone.now()
    if due_window == "overdue":
        return tasks.filter(due_at__lt=now).exclude(
            status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
        )
    if due_window == "next_24_hours":
        return tasks.filter(due_at__gte=now, due_at__lte=now + timezone.timedelta(hours=24))
    if due_window == "next_7_days":
        return tasks.filter(due_at__gte=now, due_at__lte=now + timezone.timedelta(days=7))
    return tasks


def grouped_counts(*, tasks: QuerySet[Task], field: str) -> list[dict]:
    """Return grouped task counts."""
    return [
        {"value": row[field], "count": row["count"]}
        for row in tasks.values(field).annotate(count=Count("id")).order_by(field)
    ]


def technician_rows(*, tasks: QuerySet[Task]) -> list[dict]:
    """Return task count rows grouped by assignee."""
    grouped = (
        tasks.values("assignee_id", "assignee__email", "assignee__display_name")
        .annotate(
            open_count=Count("id"),
            oldest_due_at=Min("due_at"),
        )
        .order_by("-open_count", "assignee__email")
    )
    return [
        {
            "assignee": {
                "id": row["assignee_id"],
                "email": row["assignee__email"],
                "display_name": row["assignee__display_name"],
            },
            "open_count": row["open_count"],
            "oldest_due_at": row["oldest_due_at"],
        }
        for row in grouped
    ]


def task_rows(*, tasks: QuerySet[Task]) -> list[dict]:
    """Return task summary rows."""
    return [
        {
            "id": task.id,
            "project_id": task.project_id,
            "project_name": task.project.name,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "due_at": task.due_at,
            "assignee": {
                "id": task.assignee_id,
                "email": task.assignee.email,
                "display_name": task.assignee.display_name,
            },
            "drilldown": {"type": "task_detail", "project_id": task.project_id, "task_id": task.id},
        }
        for task in tasks.order_by("due_at", "-created_at", "-id")[:10]
    ]


def recent_activity_items(*, user: Any, filters: dict) -> list[dict]:
    """Return recent activity visible to a user."""
    visible_project_ids = list(
        project_selectors.visible_projects_for_user(user).values_list("id", flat=True)
    )
    project_ids = filters.get("project_ids") or visible_project_ids
    project_ids = [project_id for project_id in project_ids if project_id in visible_project_ids]
    logs = (
        AuditLog.objects.filter(project_id__in=project_ids)
        .select_related("actor", "project")
        .order_by("-created_at", "-id")[:10]
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "project_id": log.project_id,
            "project_name": log.project.name if log.project else "",
            "actor": user_summary(log.actor),
            "created_at": log.created_at,
            "drilldown": activity_drilldown(log),
        }
        for log in logs
    ]


def task_list_drilldown(*, filters: dict) -> dict:
    """Return a task-list drill-down payload."""
    return {"type": "task_list", "filters": filters}


def activity_drilldown(log: AuditLog) -> dict:
    """Return a drill-down payload for an activity item."""
    if log.entity_type == "task":
        return {"type": "task_detail", "project_id": log.project_id, "task_id": log.entity_id}
    return {"type": "project_detail", "project_id": log.project_id}


def user_summary(user: Any) -> dict | None:
    """Return a public user summary."""
    if user is None:
        return None
    return {"id": user.id, "email": user.email, "display_name": user.display_name}
