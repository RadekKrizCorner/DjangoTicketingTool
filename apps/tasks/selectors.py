"""Task query selectors."""

from http import HTTPStatus
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from apps.common.errors import DomainError
from apps.projects import selectors as project_selectors
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment, TaskWatcher
from apps.tasks.policies import can_read_task


def non_deleted_tasks() -> QuerySet[Task]:
    """Return tasks that have not been soft deleted."""
    return Task.objects.filter(
        deleted_at__isnull=True,
        project__deleted_at__isnull=True,
    ).select_related("project", "assignee")


def visible_tasks_for_project(*, user: Any, project: Project) -> QuerySet[Task]:
    """Return tasks visible to a user for a project."""
    membership = project_selectors.membership_for_user(project=project, user=user)
    if not can_read_task(membership=membership, project=project):
        return Task.objects.none()
    return non_deleted_tasks().filter(project=project).order_by("-created_at", "-id")


def task_for_user_or_404(*, user: Any, project: Project, task_id: int) -> Task:
    """Return a visible task or raise not found."""
    task = visible_tasks_for_project(user=user, project=project).filter(pk=task_id).first()
    if task is None:
        raise_not_found()
    return task


def comments_for_task(*, task: Task) -> QuerySet[TaskComment]:
    """Return non-deleted comments for a task."""
    return (
        TaskComment.objects.filter(task=task, deleted_at__isnull=True)
        .select_related("author", "task")
        .order_by("created_at", "id")
    )


def comment_for_task_or_404(*, task: Task, comment_id: int) -> TaskComment:
    """Return a non-deleted task comment or raise not found."""
    comment = comments_for_task(task=task).filter(pk=comment_id).first()
    if comment is None:
        raise_not_found()
    return comment


def active_watchers_for_task(*, task: Task) -> QuerySet[TaskWatcher]:
    """Return active watchers who still belong to the task project."""
    return (
        TaskWatcher.objects.filter(
            task=task,
            deleted_at__isnull=True,
            user__project_memberships__project=task.project,
            user__project_memberships__deleted_at__isnull=True,
        )
        .select_related("user", "task", "task__project")
        .order_by("user_id", "id")
    )


def task_is_watched_by_user(*, task: Task, user: Any) -> bool:
    """Return whether a user actively watches a task."""
    if not getattr(user, "is_authenticated", False):
        return False
    return active_watchers_for_task(task=task).filter(user=user).exists()


def assigned_tasks_for_user(*, user: Any) -> QuerySet[Task]:
    """Return active tasks assigned to a user."""
    return non_deleted_tasks().filter(assignee=user).order_by("due_at", "-created_at", "-id")


def due_soon_tasks_for_user(*, user: Any) -> QuerySet[Task]:
    """Return incomplete tasks due soon for a user."""
    now = timezone.now()
    return assigned_tasks_for_user(user=user).filter(
        due_at__isnull=False,
        due_at__gte=now,
        due_at__lte=now + timezone.timedelta(hours=24),
    ).exclude(status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED])


def raise_not_found() -> None:
    """Raise the standard task not-found error."""
    raise DomainError(
        code="not_found",
        detail="Task or comment was not found.",
        status_code=HTTPStatus.NOT_FOUND,
    )
