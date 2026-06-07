"""UI capability helpers for project API output."""

from typing import Any

from apps.projects import policies, selectors
from apps.projects.models import Project, ProjectMembership
from apps.tasks import policies as task_policies


def membership_for_context(
    *,
    user: Any,
    project: Project,
    membership_map: dict[int, ProjectMembership] | None = None,
) -> ProjectMembership | None:
    """Return the current user's membership for a project."""
    if not getattr(user, "is_authenticated", False):
        return None
    if membership_map is not None:
        return membership_map.get(project.id)
    return selectors.membership_for_user(project=project, user=user)


def membership_summary(membership: ProjectMembership | None) -> dict | None:
    """Return a small membership summary for UI state."""
    if membership is None:
        return None
    return {"id": membership.id, "role": membership.role}


def project_capabilities(
    *,
    user: Any,
    project: Project,
    membership: ProjectMembership | None,
) -> dict[str, bool]:
    """Return UI capabilities for one project."""
    can_manage = policies.can_manage_members(actor=user, project=project, membership=membership)
    can_delete = policies.can_delete_project(actor=user, project=project, membership=membership)
    can_schedule = policies.can_schedule_project(actor=user, project=project, membership=membership)
    can_transfer = policies.can_transfer_project(actor=user, project=project, membership=membership)
    can_audit = policies.can_read_audit_log(actor=user, project=project, membership=membership)
    can_close = (
        project.state == Project.State.ACTIVE
        and policies.can_close_project(actor=user, project=project, membership=membership)
    )
    can_reopen = (
        project.state == Project.State.CLOSED
        and policies.can_reopen_project(actor=user, project=project, membership=membership)
    )
    can_write_task = task_policies.can_write_task(membership=membership, project=project)
    can_comment = task_policies.can_comment_task(
        actor=user,
        membership=membership,
        project=project,
    )
    return {
        "can_update": can_manage,
        "can_delete": can_delete,
        "can_manage_members": can_manage,
        "can_transfer_ownership": can_transfer,
        "can_schedule": can_schedule,
        "can_close": can_close,
        "can_reopen": can_reopen,
        "can_read_audit_log": can_audit,
        "can_create_task": can_write_task,
        "can_comment": can_comment,
        "can_upload_task_attachment": can_write_task,
        "can_upload_comment_attachment": can_comment,
    }
