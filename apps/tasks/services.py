"""Task business services."""

from http import HTTPStatus
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_audit_log
from apps.common.errors import DomainError
from apps.notifications.services import create_notification
from apps.projects import selectors as project_selectors
from apps.projects.models import Project, ProjectMembership
from apps.tasks import policies, selectors
from apps.tasks.models import Task, TaskComment, TaskWatcher
from apps.tasks.workflow import is_transition_allowed

TASK_UPDATE_FIELDS = {"title", "description", "assignee", "priority", "due_at"}


def create_task(*, actor: Any, project: Project, data: dict) -> Task:
    """Create a task in an active project."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_task_write(actor=actor, project=locked_project)
        assignee = data["assignee"]
        ensure_project_member(project=locked_project, user=assignee)
        task = Task.objects.create(
            project=locked_project,
            title=data["title"],
            description=data.get("description", ""),
            assignee=assignee,
            priority=data.get("priority", Task.Priority.MEDIUM),
            due_at=data.get("due_at"),
            created_by=actor,
            updated_by=actor,
        )
        record_audit_log(
            actor=actor,
            action="task.created",
            entity_type="task",
            entity_id=task.id,
            project=locked_project,
            after=task_snapshot(task),
        )
        upsert_task_watcher(actor=actor, task=task, user=actor)
        upsert_task_watcher(actor=actor, task=task, user=assignee)
        notify_task_assigned(
            actor=actor,
            task=task,
            assignee=assignee,
            key_suffix=f"created:{datetime_value(task.created_at)}",
        )
    return task


def update_task(*, actor: Any, task: Task, data: dict) -> Task:
    """Update writable task fields."""
    update_data = {key: value for key, value in data.items() if key in TASK_UPDATE_FIELDS}
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_task_write(actor=actor, project=locked_task.project)
        if "assignee" in update_data:
            ensure_project_member(project=locked_task.project, user=update_data["assignee"])
        if not update_data:
            return locked_task

        before = task_snapshot(locked_task)
        previous_assignee_id = locked_task.assignee_id
        for field, value in update_data.items():
            setattr(locked_task, field, value)
        locked_task.updated_by = actor
        locked_task.save(update_fields=[*update_data, "updated_by", "updated_at"])
        excluded_user_ids = set()
        if "assignee" in update_data and locked_task.assignee_id != previous_assignee_id:
            assigned_user = update_data["assignee"]
            excluded_user_ids.add(assigned_user.id)
            upsert_task_watcher(actor=actor, task=locked_task, user=assigned_user)
            notify_task_assigned(
                actor=actor,
                task=locked_task,
                assignee=assigned_user,
                key_suffix=f"updated:{datetime_value(locked_task.updated_at)}",
            )
        record_audit_log(
            actor=actor,
            action="task.updated",
            entity_type="task",
            entity_id=locked_task.id,
            project=locked_task.project,
            before=before,
            after=task_snapshot(locked_task),
        )
        notify_task_watchers(
            actor=actor,
            task=locked_task,
            type="task_updated",
            title=f"Task updated: {locked_task.title}",
            message=f"Task {locked_task.title} was updated.",
            key_suffix=f"updated:{datetime_value(locked_task.updated_at)}",
            exclude_user_ids=excluded_user_ids,
        )
    return locked_task


def transition_task(
    *,
    actor: Any,
    task: Task,
    target_status: str,
    note: str = "",
) -> Task:
    """Move a task to a new workflow status."""
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_task_write(actor=actor, project=locked_task.project)
        if not is_transition_allowed(current=locked_task.status, target=target_status):
            raise DomainError(
                code="invalid_transition",
                detail="Task status transition is not allowed.",
                field="status",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        before = task_snapshot(locked_task)
        locked_task.status = target_status
        locked_task.updated_by = actor
        locked_task.save(update_fields=["status", "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="task.transitioned",
            entity_type="task",
            entity_id=locked_task.id,
            project=locked_task.project,
            before=before,
            after=task_snapshot(locked_task),
            metadata={"note": note} if note else {},
        )
        notify_task_watchers(
            actor=actor,
            task=locked_task,
            type="task_transitioned",
            title=f"Task status changed: {locked_task.title}",
            message=f"Task {locked_task.title} moved to {locked_task.status}.",
            key_suffix=f"transitioned:{locked_task.status}:{datetime_value(locked_task.updated_at)}",
        )
    return locked_task


def soft_delete_task(*, actor: Any, task: Task) -> None:
    """Soft delete a task."""
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_task_write(actor=actor, project=locked_task.project)
        before = task_snapshot(locked_task)
        now = timezone.now()
        locked_task.deleted_at = now
        locked_task.deleted_by = actor
        locked_task.updated_by = actor
        locked_task.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="task.deleted",
            entity_type="task",
            entity_id=locked_task.id,
            project=locked_task.project,
            before=before,
            after=task_snapshot(locked_task),
        )
        notify_task_watchers(
            actor=actor,
            task=locked_task,
            type="task_deleted",
            title=f"Task deleted: {locked_task.title}",
            message=f"Task {locked_task.title} was deleted.",
            key_suffix=f"deleted:{datetime_value(locked_task.deleted_at)}",
        )


def create_comment(*, actor: Any, task: Task, body: str) -> TaskComment:
    """Create a task comment."""
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_comment(actor=actor, project=locked_task.project)
        comment = TaskComment.objects.create(
            task=locked_task,
            author=actor,
            body=body,
            created_by=actor,
            updated_by=actor,
        )
        record_audit_log(
            actor=actor,
            action="task_comment.created",
            entity_type="task_comment",
            entity_id=comment.id,
            project=locked_task.project,
            after=comment_snapshot(comment),
        )
        notify_task_watchers(
            actor=actor,
            task=locked_task,
            type="task_comment_created",
            title=f"New comment on task: {locked_task.title}",
            message=f"Task {locked_task.title} has a new comment.",
            key_suffix=f"comment:{comment.id}:created",
        )
    return comment


def update_comment(*, actor: Any, comment: TaskComment, body: str) -> TaskComment:
    """Update a user's own task comment."""
    with transaction.atomic():
        locked_comment = lock_comment(comment=comment)
        if locked_comment.author_id != actor.id:
            raise_permission_denied()
        before = comment_snapshot(locked_comment)
        locked_comment.body = body
        locked_comment.updated_by = actor
        locked_comment.save(update_fields=["body", "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="task_comment.updated",
            entity_type="task_comment",
            entity_id=locked_comment.id,
            project=locked_comment.task.project,
            before=before,
            after=comment_snapshot(locked_comment),
        )
        notify_task_watchers(
            actor=actor,
            task=locked_comment.task,
            type="task_comment_updated",
            title=f"Comment updated on task: {locked_comment.task.title}",
            message=f"A comment on task {locked_comment.task.title} was updated.",
            key_suffix=f"comment:{locked_comment.id}:updated:{datetime_value(locked_comment.updated_at)}",
        )
    return locked_comment


def soft_delete_comment(*, actor: Any, comment: TaskComment) -> None:
    """Soft delete a task comment."""
    with transaction.atomic():
        locked_comment = lock_comment(comment=comment)
        membership = project_selectors.membership_for_user(
            project=locked_comment.task.project,
            user=actor,
        )
        if not policies.can_delete_comment(
            actor=actor,
            membership=membership,
            author_id=locked_comment.author_id,
        ):
            raise_permission_denied()
        before = comment_snapshot(locked_comment)
        now = timezone.now()
        locked_comment.deleted_at = now
        locked_comment.deleted_by = actor
        locked_comment.updated_by = actor
        locked_comment.save(
            update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"]
        )
        record_audit_log(
            actor=actor,
            action="task_comment.deleted",
            entity_type="task_comment",
            entity_id=locked_comment.id,
            project=locked_comment.task.project,
            before=before,
            after=comment_snapshot(locked_comment),
        )
        notify_task_watchers(
            actor=actor,
            task=locked_comment.task,
            type="task_comment_deleted",
            title=f"Comment deleted on task: {locked_comment.task.title}",
            message=f"A comment on task {locked_comment.task.title} was deleted.",
            key_suffix=f"comment:{locked_comment.id}:deleted:{datetime_value(locked_comment.deleted_at)}",
        )


def watch_task(*, actor: Any, task: Task) -> TaskWatcher:
    """Subscribe an active project member to a task."""
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_active_project_member(project=locked_task.project, user=actor)
        return upsert_task_watcher(actor=actor, task=locked_task, user=actor)


def unwatch_task(*, actor: Any, task: Task) -> None:
    """Remove an active project member's task watcher subscription."""
    with transaction.atomic():
        locked_task = lock_task(task=task)
        ensure_active_project_member(project=locked_task.project, user=actor)
        watcher = TaskWatcher.objects.filter(
            task=locked_task,
            user=actor,
            deleted_at__isnull=True,
        ).first()
        if watcher is None:
            return
        now = timezone.now()
        watcher.deleted_at = now
        watcher.deleted_by = actor
        watcher.updated_by = actor
        watcher.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])


def lock_project(*, project: Project) -> Project:
    """Lock and return the current project row."""
    return Project.objects.select_for_update().get(pk=project.pk)


def lock_task(*, task: Task) -> Task:
    """Lock and return the current task row."""
    return (
        Task.objects.select_for_update()
        .select_related("project", "assignee")
        .get(pk=task.pk, deleted_at__isnull=True)
    )


def lock_comment(*, comment: TaskComment) -> TaskComment:
    """Lock and return the current comment row."""
    return (
        TaskComment.objects.select_for_update()
        .select_related("task", "task__project", "author")
        .get(pk=comment.pk, deleted_at__isnull=True)
    )


def ensure_task_write(*, actor: Any, project: Project) -> None:
    """Raise unless actor can mutate tasks in the project."""
    membership = project_selectors.membership_for_user(project=project, user=actor)
    if not policies.can_write_task(membership=membership, project=project):
        if project.state == Project.State.CLOSED:
            raise DomainError(
                code="project_closed",
                detail="Project is closed.",
                status_code=HTTPStatus.CONFLICT,
            )
        raise_permission_denied()


def ensure_comment(*, actor: Any, project: Project) -> None:
    """Raise unless actor can comment in the project."""
    membership = project_selectors.membership_for_user(project=project, user=actor)
    if not policies.can_comment_task(actor=actor, membership=membership, project=project):
        raise_permission_denied()


def ensure_project_member(*, project: Project, user: Any) -> ProjectMembership:
    """Return a project membership for a user or raise validation error."""
    membership = project_selectors.membership_for_user(project=project, user=user)
    if membership is None:
        raise DomainError(
            code="validation_error",
            detail="Assignee must be an active project member.",
            field="assignee_id",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return membership


def ensure_active_project_member(*, project: Project, user: Any) -> ProjectMembership:
    """Return an active project membership or raise permission denied."""
    membership = project_selectors.membership_for_user(project=project, user=user)
    if membership is None:
        raise_permission_denied()
    return membership


def upsert_task_watcher(*, actor: Any, task: Task, user: Any) -> TaskWatcher:
    """Create or restore a task watcher row."""
    active_watcher = TaskWatcher.objects.filter(
        task=task,
        user=user,
        deleted_at__isnull=True,
    ).first()
    if active_watcher is not None:
        return active_watcher

    deleted_watcher = (
        TaskWatcher.objects.filter(task=task, user=user)
        .exclude(deleted_at__isnull=True)
        .order_by("-id")
        .first()
    )
    if deleted_watcher is not None:
        deleted_watcher.deleted_at = None
        deleted_watcher.deleted_by = None
        deleted_watcher.updated_by = actor
        try:
            deleted_watcher.save(
                update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"]
            )
        except IntegrityError:
            return TaskWatcher.objects.get(task=task, user=user, deleted_at__isnull=True)
        return deleted_watcher

    try:
        return TaskWatcher.objects.create(task=task, user=user, created_by=actor, updated_by=actor)
    except IntegrityError:
        return TaskWatcher.objects.get(task=task, user=user, deleted_at__isnull=True)


def notify_task_assigned(*, actor: Any, task: Task, assignee: Any, key_suffix: str) -> None:
    """Create an assignment notification for a task assignee."""
    if assignee.id == actor.id:
        return
    create_notification(
        user=assignee,
        type="task_assigned",
        title=f"Task assigned: {task.title}",
        message=f"Task {task.title} was assigned to you.",
        dedupe_key=f"task:{task.id}:assigned:{key_suffix}:user:{assignee.id}",
        project=task.project,
        task=task,
    )


def notify_task_watchers(
    *,
    actor: Any,
    task: Task,
    type: str,
    title: str,
    message: str,
    key_suffix: str,
    exclude_user_ids: set[int] | None = None,
) -> None:
    """Create notifications for active task watchers except excluded users."""
    excluded_ids = {actor.id, *(exclude_user_ids or set())}
    watchers = selectors.active_watchers_for_task(task=task).exclude(user_id__in=excluded_ids)
    for watcher in watchers:
        create_notification(
            user=watcher.user,
            type=type,
            title=title,
            message=message,
            dedupe_key=f"task:{task.id}:{key_suffix}:user:{watcher.user_id}",
            project=task.project,
            task=task,
        )


def task_snapshot(task: Task) -> dict:
    """Return a JSON-safe task snapshot."""
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "status": task.status,
        "priority": task.priority,
        "due_at": datetime_value(task.due_at),
        "deleted_at": datetime_value(task.deleted_at),
    }


def comment_snapshot(comment: TaskComment) -> dict:
    """Return a JSON-safe comment snapshot."""
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "author_id": comment.author_id,
        "body": comment.body,
        "deleted_at": datetime_value(comment.deleted_at),
    }


def datetime_value(value) -> str | None:
    """Return an ISO formatted datetime or none."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def raise_permission_denied() -> None:
    """Raise a permission-denied domain error."""
    raise DomainError(
        code="permission_denied",
        detail="You do not have permission to perform this action.",
        status_code=HTTPStatus.FORBIDDEN,
    )
