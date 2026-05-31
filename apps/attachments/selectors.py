"""Attachment query selectors."""

from http import HTTPStatus
from typing import Any

from django.db.models import Q, QuerySet

from apps.attachments.models import Attachment
from apps.common.errors import DomainError
from apps.projects import selectors as project_selectors
from apps.tasks import selectors as task_selectors


def non_deleted_attachments() -> QuerySet[Attachment]:
    """Return attachments that have not been soft deleted."""
    return Attachment.objects.filter(deleted_at__isnull=True).select_related(
        "task",
        "task__project",
        "comment",
        "comment__task",
        "comment__task__project",
        "uploaded_by",
    )


def attachments_for_task(*, task) -> QuerySet[Attachment]:
    """Return non-deleted attachments for a task."""
    return non_deleted_attachments().filter(task=task).order_by("-created_at", "-id")


def attachments_for_comment(*, comment) -> QuerySet[Attachment]:
    """Return non-deleted attachments for a comment."""
    return non_deleted_attachments().filter(comment=comment).order_by("-created_at", "-id")


def attachment_or_404(*, attachment_id: int) -> Attachment:
    """Return a non-deleted attachment or raise not found."""
    attachment = non_deleted_attachments().filter(pk=attachment_id).first()
    if attachment is None:
        raise DomainError(
            code="not_found",
            detail="Attachment was not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )
    return attachment


def project_for_attachment(attachment: Attachment):
    """Return the project that owns an attachment."""
    if attachment.task_id:
        return attachment.task.project
    return attachment.comment.task.project


def can_read_attachment(*, user: Any, attachment: Attachment) -> bool:
    """Return whether a user can read an attachment."""
    project = project_for_attachment(attachment)
    task = attachment.task or attachment.comment.task
    try:
        task_selectors.task_for_user_or_404(user=user, project=project, task_id=task.id)
    except DomainError:
        return False
    return True


def project_attachment_filter(project) -> Q:
    """Return a filter matching attachments for a project."""
    return Q(task__project=project) | Q(comment__task__project=project)


def membership_for_attachment(*, user: Any, attachment: Attachment):
    """Return the user's membership for an attachment project."""
    return project_selectors.membership_for_user(
        project=project_for_attachment(attachment),
        user=user,
    )
