"""Dashboard query selectors."""

from http import HTTPStatus
from typing import Any

from django.db.models import Q, QuerySet

from apps.common.errors import DomainError
from apps.dashboards import policies
from apps.dashboards.models import Dashboard, DashboardShare, DashboardWidget


def non_deleted_dashboards() -> QuerySet[Dashboard]:
    """Return dashboards that have not been soft deleted."""
    return Dashboard.objects.filter(deleted_at__isnull=True).select_related("owner")


def active_dashboard_widgets() -> QuerySet[DashboardWidget]:
    """Return widgets that have not been soft deleted."""
    return DashboardWidget.objects.filter(
        deleted_at__isnull=True,
        dashboard__deleted_at__isnull=True,
    ).select_related("dashboard", "dashboard__owner")


def active_dashboard_shares() -> QuerySet[DashboardShare]:
    """Return shares that have not been soft deleted."""
    return DashboardShare.objects.filter(
        deleted_at__isnull=True,
        dashboard__deleted_at__isnull=True,
    ).select_related("dashboard", "user", "project")


def visible_dashboards_for_user(*, user: Any) -> QuerySet[Dashboard]:
    """Return dashboards visible to a user."""
    if not getattr(user, "is_authenticated", False):
        return Dashboard.objects.none()
    return (
        non_deleted_dashboards()
        .filter(
            Q(owner=user)
            | Q(
                shares__target_type=DashboardShare.TargetType.USER,
                shares__user=user,
                shares__deleted_at__isnull=True,
            )
            | Q(
                shares__target_type=DashboardShare.TargetType.PROJECT_MEMBERS,
                shares__deleted_at__isnull=True,
                shares__project__memberships__user=user,
                shares__project__memberships__deleted_at__isnull=True,
            )
        )
        .distinct()
        .order_by("name", "id")
    )


def dashboard_access_for_user(*, dashboard: Dashboard, user: Any) -> str:
    """Return a user's effective dashboard access."""
    if not getattr(user, "is_authenticated", False):
        return policies.ACCESS_NONE
    if dashboard.owner_id == user.id:
        return policies.ACCESS_OWNER

    shares = active_dashboard_shares().filter(dashboard=dashboard).filter(
        Q(target_type=DashboardShare.TargetType.USER, user=user)
        | Q(
            target_type=DashboardShare.TargetType.PROJECT_MEMBERS,
            project__memberships__user=user,
            project__memberships__deleted_at__isnull=True,
        )
    )
    access = policies.ACCESS_NONE
    for share in shares:
        if policies.access_allows(actual=share.access, required=access):
            access = share.access
    return access


def dashboard_for_user_or_404(
    *,
    user: Any,
    dashboard_id: int,
    required_access: str = policies.ACCESS_VIEWER,
) -> Dashboard:
    """Return an accessible dashboard or raise an API error."""
    dashboard = non_deleted_dashboards().filter(pk=dashboard_id).first()
    if dashboard is None:
        raise_not_found()
    access = dashboard_access_for_user(dashboard=dashboard, user=user)
    if access == policies.ACCESS_NONE:
        raise_not_found()
    if not policies.access_allows(actual=access, required=required_access):
        raise_permission_denied()
    dashboard.effective_access = access
    return dashboard


def widgets_for_dashboard(*, dashboard: Dashboard) -> QuerySet[DashboardWidget]:
    """Return active widgets for a dashboard."""
    return active_dashboard_widgets().filter(dashboard=dashboard).order_by("order", "id")


def widget_for_dashboard_or_404(
    *,
    dashboard: Dashboard,
    widget_id: int,
) -> DashboardWidget:
    """Return an active dashboard widget or raise not found."""
    widget = widgets_for_dashboard(dashboard=dashboard).filter(pk=widget_id).first()
    if widget is None:
        raise_not_found()
    return widget


def shares_for_dashboard(*, dashboard: Dashboard) -> QuerySet[DashboardShare]:
    """Return active shares for a dashboard."""
    return active_dashboard_shares().filter(dashboard=dashboard).order_by("target_type", "id")


def raise_not_found() -> None:
    """Raise the standard dashboard not-found error."""
    raise DomainError(
        code="not_found",
        detail="Dashboard was not found.",
        status_code=HTTPStatus.NOT_FOUND,
    )


def raise_permission_denied() -> None:
    """Raise the standard dashboard permission error."""
    raise DomainError(
        code="permission_denied",
        detail="You do not have permission to manage this dashboard.",
        status_code=HTTPStatus.FORBIDDEN,
    )
