"""Task permission policies."""

from typing import Any

from apps.projects.models import Project, ProjectMembership

WRITABLE_TASK_ROLES = {
    ProjectMembership.Role.OWNER,
    ProjectMembership.Role.MANAGER,
    ProjectMembership.Role.MEMBER,
}
COMMENT_ROLES = {
    ProjectMembership.Role.OWNER,
    ProjectMembership.Role.MANAGER,
    ProjectMembership.Role.MEMBER,
    ProjectMembership.Role.VIEWER,
}


def can_read_task(*, membership: ProjectMembership | None, project: Project) -> bool:
    """Return whether a task is readable."""
    return bool(membership or project.visibility == Project.Visibility.PUBLIC)


def can_write_task(*, membership: ProjectMembership | None, project: Project) -> bool:
    """Return whether a task can be created or changed."""
    return bool(
        project.state == Project.State.ACTIVE
        and membership
        and membership.role in WRITABLE_TASK_ROLES
    )


def can_comment_task(
    *,
    actor: Any,
    membership: ProjectMembership | None,
    project: Project,
) -> bool:
    """Return whether a user can comment on a task."""
    if not getattr(actor, "is_authenticated", False):
        return False
    if membership and membership.role in COMMENT_ROLES:
        return True
    return bool(
        project.visibility == Project.Visibility.PUBLIC
        and project.public_comment_policy == Project.PublicCommentPolicy.AUTHENTICATED_USERS
    )


def can_delete_comment(
    *,
    actor: Any,
    membership: ProjectMembership | None,
    author_id: int,
) -> bool:
    """Return whether a user can delete a comment."""
    if actor.id == author_id:
        return True
    return bool(
        membership
        and membership.role in {ProjectMembership.Role.OWNER, ProjectMembership.Role.MANAGER}
    )


def can_delete_attachment(
    *,
    actor: Any,
    membership: ProjectMembership | None,
    uploaded_by_id: int,
) -> bool:
    """Return whether a user can delete an attachment."""
    if actor.id == uploaded_by_id:
        return True
    return bool(
        membership
        and membership.role in {ProjectMembership.Role.OWNER, ProjectMembership.Role.MANAGER}
    )
