"""Dashboard permission policies."""

from typing import Any

from apps.dashboards.models import Dashboard, DashboardShare

ACCESS_NONE = "none"
ACCESS_VIEWER = DashboardShare.Access.VIEWER
ACCESS_EDITOR = DashboardShare.Access.EDITOR
ACCESS_OWNER = "owner"

ACCESS_RANK = {
    ACCESS_NONE: 0,
    ACCESS_VIEWER: 1,
    ACCESS_EDITOR: 2,
    ACCESS_OWNER: 3,
}


def access_allows(*, actual: str, required: str) -> bool:
    """Return whether an access level satisfies a requirement."""
    return ACCESS_RANK.get(actual, 0) >= ACCESS_RANK.get(required, 0)


def can_view_dashboard(*, access: str) -> bool:
    """Return whether an access level can view a dashboard."""
    return access_allows(actual=access, required=ACCESS_VIEWER)


def can_edit_dashboard(*, access: str) -> bool:
    """Return whether an access level can edit a dashboard."""
    return access_allows(actual=access, required=ACCESS_EDITOR)


def can_manage_dashboard_shares(*, actor: Any, dashboard: Dashboard) -> bool:
    """Return whether an actor can manage dashboard shares."""
    return bool(actor and actor.is_authenticated and dashboard.owner_id == actor.id)


def can_delete_dashboard(*, actor: Any, dashboard: Dashboard) -> bool:
    """Return whether an actor can delete a dashboard."""
    return can_manage_dashboard_shares(actor=actor, dashboard=dashboard)


def dashboard_capabilities(*, actor: Any, dashboard: Dashboard, access: str) -> dict[str, bool]:
    """Return UI capabilities for a dashboard."""
    return {
        "can_view": can_view_dashboard(access=access),
        "can_edit": can_edit_dashboard(access=access),
        "can_manage_shares": can_manage_dashboard_shares(actor=actor, dashboard=dashboard),
        "can_delete": can_delete_dashboard(actor=actor, dashboard=dashboard),
    }
