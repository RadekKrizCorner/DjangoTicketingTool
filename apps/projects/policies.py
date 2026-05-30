"""Project permission policies."""

from typing import Any

from apps.projects.models import Project, ProjectMembership

ACTION_READ = "read"
ACTION_MANAGE_MEMBERS = "manage_members"
ACTION_DELETE = "delete"
ACTION_SCHEDULE = "schedule"
ACTION_TRANSFER = "transfer"
ACTION_AUDIT = "audit"
ACTION_CLOSE = "close"
ACTION_REOPEN = "reopen"

OWNER_ACTIONS = {
    ACTION_READ,
    ACTION_MANAGE_MEMBERS,
    ACTION_DELETE,
    ACTION_SCHEDULE,
    ACTION_TRANSFER,
    ACTION_AUDIT,
    ACTION_CLOSE,
    ACTION_REOPEN,
}
MANAGER_ACTIONS = {ACTION_READ}
MEMBER_ACTIONS = {ACTION_READ}
VIEWER_ACTIONS = {ACTION_READ}
STAFF_ACTIONS = {ACTION_SCHEDULE, ACTION_CLOSE, ACTION_REOPEN}

ROLE_ACTIONS = {
    ProjectMembership.Role.OWNER: OWNER_ACTIONS,
    ProjectMembership.Role.MANAGER: MANAGER_ACTIONS,
    ProjectMembership.Role.MEMBER: MEMBER_ACTIONS,
    ProjectMembership.Role.VIEWER: VIEWER_ACTIONS,
}


def role_allows_action(*, role: str | None, action: str) -> bool:
    """Return whether a role allows an action."""
    return action in ROLE_ACTIONS.get(role, set())


def staff_allows_action(*, action: str) -> bool:
    """Return whether staff override allows an action."""
    return action in STAFF_ACTIONS


def can_read_project(*, membership: ProjectMembership | None) -> bool:
    """Return whether a membership can read a project."""
    return role_allows_action(role=_role(membership), action=ACTION_READ)


def can_manage_members(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can manage project members."""
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_delete_project(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can delete the project."""
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_schedule_project(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can schedule project lifecycle changes."""
    if _is_staff(actor):
        return staff_allows_action(action=ACTION_SCHEDULE)
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_transfer_project(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can transfer project ownership."""
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_read_audit_log(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can read project audit logs."""
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_close_project(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can close the project."""
    if _is_staff(actor):
        return staff_allows_action(action=ACTION_CLOSE)
    return _is_project_owner(actor=actor, project=project, membership=membership)


def can_reopen_project(
    *, actor: Any, project: Project, membership: ProjectMembership | None
) -> bool:
    """Return whether the actor can reopen the project."""
    if _is_staff(actor):
        return staff_allows_action(action=ACTION_REOPEN)
    return _is_project_owner(actor=actor, project=project, membership=membership)


def _is_project_owner(
    *,
    actor: Any,
    project: Project,
    membership: ProjectMembership | None,
) -> bool:
    """Return whether the actor is the current project owner."""
    return bool(
        actor
        and project.owner_id == actor.id
        and membership
        and membership.role == ProjectMembership.Role.OWNER
    )


def _is_staff(actor: Any) -> bool:
    """Return whether the actor is an active staff user."""
    return bool(actor and actor.is_active and actor.is_staff)


def _role(membership: ProjectMembership | None) -> str | None:
    """Return the role from a membership."""
    if membership is None:
        return None
    return membership.role
