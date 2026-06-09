"""Dashboard business services."""

from http import HTTPStatus
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.common.errors import DomainError
from apps.dashboards import policies, selectors, validators
from apps.dashboards.models import Dashboard, DashboardShare, DashboardWidget
from apps.projects.models import Project

GRID_COLUMNS = 12
MAX_GRID_HEIGHT = 100


def create_dashboard(*, actor: Any, name: str) -> Dashboard:
    """Create a dashboard owned by an actor."""
    return Dashboard.objects.create(name=name, owner=actor, created_by=actor, updated_by=actor)


def update_dashboard(*, actor: Any, dashboard: Dashboard, data: dict) -> Dashboard:
    """Update editable dashboard fields."""
    ensure_dashboard_edit(actor=actor, dashboard=dashboard)
    if "name" in data:
        dashboard.name = data["name"]
    dashboard.updated_by = actor
    dashboard.save(update_fields=["name", "updated_by", "updated_at"])
    return dashboard


def soft_delete_dashboard(*, actor: Any, dashboard: Dashboard) -> None:
    """Soft delete a dashboard."""
    if not policies.can_delete_dashboard(actor=actor, dashboard=dashboard):
        selectors.raise_permission_denied()
    now = timezone.now()
    dashboard.deleted_at = now
    dashboard.deleted_by = actor
    dashboard.updated_by = actor
    dashboard.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])


def create_widget(*, actor: Any, dashboard: Dashboard, data: dict) -> DashboardWidget:
    """Create a dashboard widget."""
    ensure_dashboard_edit(actor=actor, dashboard=dashboard)
    config = validate_widget_config(config=data.get("config", {}))
    layout = widget_layout(data)
    validate_layout_items(
        layout_items=[layout],
        existing_widgets=list(selectors.widgets_for_dashboard(dashboard=dashboard)),
    )
    return DashboardWidget.objects.create(
        dashboard=dashboard,
        type=data["type"],
        title=data["title"],
        config=config,
        x=layout["x"],
        y=layout["y"],
        w=layout["w"],
        h=layout["h"],
        order=layout["order"],
        created_by=actor,
        updated_by=actor,
    )


def update_widget(*, actor: Any, widget: DashboardWidget, data: dict) -> DashboardWidget:
    """Update a dashboard widget."""
    ensure_dashboard_edit(actor=actor, dashboard=widget.dashboard)
    if "title" in data:
        widget.title = data["title"]
    if "type" in data:
        widget.type = data["type"]
    if "config" in data:
        widget.config = validate_widget_config(config=data["config"])
    layout_fields = {"x", "y", "w", "h", "order"} & set(data)
    for field in layout_fields:
        setattr(widget, field, data[field])
    if layout_fields:
        candidate = widget_layout(
            {
                "x": widget.x,
                "y": widget.y,
                "w": widget.w,
                "h": widget.h,
                "order": widget.order,
            },
            widget_id=widget.id,
        )
        others = selectors.widgets_for_dashboard(dashboard=widget.dashboard).exclude(pk=widget.id)
        validate_layout_items(layout_items=[candidate], existing_widgets=list(others))
    widget.updated_by = actor
    widget.save()
    return widget


def soft_delete_widget(*, actor: Any, widget: DashboardWidget) -> None:
    """Soft delete a dashboard widget."""
    ensure_dashboard_edit(actor=actor, dashboard=widget.dashboard)
    now = timezone.now()
    widget.deleted_at = now
    widget.deleted_by = actor
    widget.updated_by = actor
    widget.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])


def update_layout(
    *,
    actor: Any,
    dashboard: Dashboard,
    widgets: list[dict],
) -> list[DashboardWidget]:
    """Update dashboard widget layout."""
    ensure_dashboard_edit(actor=actor, dashboard=dashboard)
    widget_map = {
        widget.id: widget for widget in selectors.widgets_for_dashboard(dashboard=dashboard)
    }
    layout_items = []
    for item in widgets:
        widget_id = item["id"]
        if widget_id not in widget_map:
            selectors.raise_not_found()
        layout_items.append(widget_layout(item, widget_id=widget_id))
    updated_widget_ids = {item["id"] for item in layout_items}
    existing_widgets = [
        widget for widget_id, widget in widget_map.items() if widget_id not in updated_widget_ids
    ]
    validate_layout_items(layout_items=layout_items, existing_widgets=existing_widgets)
    with transaction.atomic():
        for item in layout_items:
            widget = widget_map[item["id"]]
            widget.x = item["x"]
            widget.y = item["y"]
            widget.w = item["w"]
            widget.h = item["h"]
            widget.order = item["order"]
            widget.updated_by = actor
            widget.save(update_fields=["x", "y", "w", "h", "order", "updated_by", "updated_at"])
    return list(selectors.widgets_for_dashboard(dashboard=dashboard))


def replace_shares(*, actor: Any, dashboard: Dashboard, shares: list[dict]) -> list[DashboardShare]:
    """Replace dashboard share rules."""
    if not policies.can_manage_dashboard_shares(actor=actor, dashboard=dashboard):
        selectors.raise_permission_denied()
    with transaction.atomic():
        now = timezone.now()
        for share in selectors.shares_for_dashboard(dashboard=dashboard):
            share.deleted_at = now
            share.deleted_by = actor
            share.updated_by = actor
            share.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])
        for item in shares:
            create_share(actor=actor, dashboard=dashboard, data=item)
    return list(selectors.shares_for_dashboard(dashboard=dashboard))


def create_share(*, actor: Any, dashboard: Dashboard, data: dict) -> DashboardShare:
    """Create a dashboard share rule."""
    target_type = data["target_type"]
    user = None
    project = None
    if target_type == DashboardShare.TargetType.USER:
        user = get_active_user_or_400(data.get("user_id"))
    if target_type == DashboardShare.TargetType.PROJECT_MEMBERS:
        project = get_active_project_or_400(data.get("project_id"))
    return DashboardShare.objects.create(
        dashboard=dashboard,
        target_type=target_type,
        user=user,
        project=project,
        access=data["access"],
        created_by=actor,
        updated_by=actor,
    )


def ensure_dashboard_edit(*, actor: Any, dashboard: Dashboard) -> None:
    """Ensure an actor can edit a dashboard."""
    access = selectors.dashboard_access_for_user(dashboard=dashboard, user=actor)
    if not policies.can_edit_dashboard(access=access):
        selectors.raise_permission_denied()


def validate_widget_config(*, config: dict) -> dict:
    """Return a validated widget config."""
    return validators.validate_task_filters(filters=config, field="config")


def widget_layout(data: dict, widget_id: int | None = None) -> dict:
    """Return normalized widget layout data."""
    layout = {
        "x": int(data.get("x", 0)),
        "y": int(data.get("y", 0)),
        "w": int(data.get("w", 3)),
        "h": int(data.get("h", 2)),
        "order": int(data.get("order", 1)),
    }
    if widget_id is not None:
        layout["id"] = widget_id
    return layout


def validate_layout_items(
    *,
    layout_items: list[dict],
    existing_widgets: list[DashboardWidget],
) -> None:
    """Validate grid bounds and collisions for layout items."""
    items = list(layout_items)
    items.extend(
        widget_layout(
            {"x": widget.x, "y": widget.y, "w": widget.w, "h": widget.h, "order": widget.order},
            widget_id=widget.id,
        )
        for widget in existing_widgets
    )
    for item in items:
        if item["x"] < 0 or item["y"] < 0 or item["w"] < 1 or item["h"] < 1:
            raise_validation_error(field="layout", detail="Widget layout values must be positive.")
        if item["x"] + item["w"] > GRID_COLUMNS:
            raise_validation_error(field="layout", detail="Widget layout exceeds grid width.")
        if item["y"] + item["h"] > MAX_GRID_HEIGHT:
            raise_validation_error(field="layout", detail="Widget layout exceeds grid height.")
    for index, item in enumerate(items):
        for other in items[index + 1 :]:
            if layouts_overlap(item, other):
                raise_validation_error(field="layout", detail="Widget layouts cannot overlap.")


def layouts_overlap(first: dict, second: dict) -> bool:
    """Return whether two grid layout rectangles overlap."""
    return not (
        first["x"] + first["w"] <= second["x"]
        or second["x"] + second["w"] <= first["x"]
        or first["y"] + first["h"] <= second["y"]
        or second["y"] + second["h"] <= first["y"]
    )


def get_active_user_or_400(user_id: int | None):
    """Return an active user or raise a validation error."""
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise_validation_error(field="user_id", detail="Active user was not found.")
    return user


def get_active_project_or_400(project_id: int | None) -> Project:
    """Return an active project or raise a validation error."""
    project = Project.objects.filter(pk=project_id, deleted_at__isnull=True).first()
    if project is None:
        raise_validation_error(field="project_id", detail="Project was not found.")
    return project


def raise_validation_error(*, field: str, detail: str) -> None:
    """Raise a dashboard validation error."""
    raise DomainError(
        code="validation_error",
        detail=detail,
        field=field,
        status_code=HTTPStatus.BAD_REQUEST,
    )
