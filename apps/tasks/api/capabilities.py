"""UI capability helpers for task API output."""

from typing import Any

from apps.projects import selectors as project_selectors
from apps.projects.models import ProjectMembership
from apps.tasks import policies, selectors
from apps.tasks.models import Task, TaskComment
from apps.tasks.workflow import ALLOWED_TRANSITIONS


def membership_for_task(*, user: Any, task: Task) -> ProjectMembership | None:
    """Return the current user's membership for a task project."""
    return project_selectors.membership_for_user(project=task.project, user=user)


def task_allowed_transitions(
    *,
    user: Any,
    task: Task,
    membership: ProjectMembership | None,
) -> list[str]:
    """Return allowed task workflow transitions for the user."""
    if not policies.can_write_task(membership=membership, project=task.project):
        return []
    return sorted(ALLOWED_TRANSITIONS.get(task.status, set()))


def task_capabilities(
    *,
    user: Any,
    task: Task,
    membership: ProjectMembership | None,
    watched: bool | None = None,
) -> dict[str, bool]:
    """Return UI capabilities for one task."""
    can_write = policies.can_write_task(membership=membership, project=task.project)
    can_comment = policies.can_comment_task(
        actor=user,
        membership=membership,
        project=task.project,
    )
    can_watch_tasks = membership is not None
    if watched is None:
        watched = selectors.task_is_watched_by_user(task=task, user=user)
    return {
        "can_update": can_write,
        "can_delete": can_write,
        "can_transition": can_write,
        "can_watch": can_watch_tasks and not watched,
        "can_unwatch": can_watch_tasks and watched,
        "can_comment": can_comment,
        "can_upload_attachment": can_write,
    }


def comment_capabilities(
    *,
    user: Any,
    comment: TaskComment,
    membership: ProjectMembership | None,
) -> dict[str, bool]:
    """Return UI capabilities for one task comment."""
    if not getattr(user, "is_authenticated", False):
        return {
            "can_update": False,
            "can_delete": False,
            "can_upload_attachment": False,
        }
    can_comment = policies.can_comment_task(
        actor=user,
        membership=membership,
        project=comment.task.project,
    )
    return {
        "can_update": getattr(user, "id", None) == comment.author_id,
        "can_delete": policies.can_delete_comment(
            actor=user,
            membership=membership,
            author_id=comment.author_id,
        ),
        "can_upload_attachment": can_comment,
    }
