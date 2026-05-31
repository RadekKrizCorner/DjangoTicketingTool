"""Attachment business services."""

import hashlib
from http import HTTPStatus
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.attachments.models import Attachment
from apps.attachments.selectors import project_attachment_filter, project_for_attachment
from apps.common.errors import DomainError
from apps.projects import selectors as project_selectors
from apps.projects.models import Project
from apps.tasks import policies as task_policies
from apps.tasks.models import Task, TaskComment

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "text/plain"}
TEXT_EXTENSIONS = {".txt", ".log", ".out", ".err"}


def create_attachment(*, actor: Any, parent: Task | TaskComment, uploaded_file) -> Attachment:
    """Create an attachment after validating type and quota."""
    project = project_for_parent(parent)
    membership = project_selectors.membership_for_user(project=project, user=actor)
    ensure_upload_allowed(actor=actor, parent=parent, project=project, membership=membership)
    validate_uploaded_file(uploaded_file=uploaded_file, project=project)
    checksum = file_checksum(uploaded_file)
    filename = Path(uploaded_file.name).name
    with transaction.atomic():
        attachment = Attachment.objects.create(
            task=parent if isinstance(parent, Task) else None,
            comment=parent if isinstance(parent, TaskComment) else None,
            uploaded_by=actor,
            original_filename=filename,
            file=uploaded_file,
            content_type=getattr(uploaded_file, "content_type", "") or "",
            size_bytes=uploaded_file.size,
            checksum_sha256=checksum,
            created_by=actor,
            updated_by=actor,
        )
    return attachment


def soft_delete_attachment(*, actor: Any, attachment: Attachment) -> None:
    """Soft delete an attachment."""
    project = project_for_attachment(attachment)
    membership = project_selectors.membership_for_user(project=project, user=actor)
    if not task_policies.can_delete_attachment(
        actor=actor,
        membership=membership,
        uploaded_by_id=attachment.uploaded_by_id,
    ):
        raise_permission_denied()
    attachment.deleted_at = timezone.now()
    attachment.deleted_by = actor
    attachment.updated_by = actor
    attachment.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])


def ensure_upload_allowed(*, actor: Any, parent: Task | TaskComment, project: Project, membership):
    """Raise unless the actor can upload to a parent object."""
    if isinstance(parent, Task):
        if not task_policies.can_write_task(membership=membership, project=project):
            if project.state == Project.State.CLOSED:
                raise DomainError(
                    code="project_closed",
                    detail="Project is closed.",
                    status_code=HTTPStatus.CONFLICT,
                )
            raise_permission_denied()
        return

    if not task_policies.can_comment_task(actor=actor, membership=membership, project=project):
        raise_permission_denied()


def validate_uploaded_file(*, uploaded_file, project: Project) -> None:
    """Validate attachment size, content type, extension, and quotas."""
    if uploaded_file.size > settings.ATTACHMENT_MAX_FILE_SIZE_BYTES:
        raise DomainError(
            code="attachment_too_large",
            detail="Attachment exceeds the per-file size limit.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    content_type = getattr(uploaded_file, "content_type", "") or ""
    suffix = Path(uploaded_file.name).suffix.lower()
    if content_type not in ALLOWED_CONTENT_TYPES or (
        content_type == "text/plain" and suffix not in TEXT_EXTENSIONS
    ):
        raise DomainError(
            code="attachment_type_not_allowed",
            detail="Attachment file type is not allowed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    if total_attachment_bytes() + uploaded_file.size > settings.ATTACHMENT_MAX_TOTAL_BYTES:
        raise_quota_exceeded("Global attachment quota would be exceeded.")
    if (
        project_attachment_bytes(project=project) + uploaded_file.size
        > settings.ATTACHMENT_MAX_PROJECT_BYTES
    ):
        raise_quota_exceeded("Project attachment quota would be exceeded.")


def file_checksum(uploaded_file) -> str:
    """Return a SHA256 checksum for an uploaded file."""
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def total_attachment_bytes() -> int:
    """Return total active attachment bytes."""
    return (
        Attachment.objects.filter(deleted_at__isnull=True).aggregate(total=Sum("size_bytes"))[
            "total"
        ]
        or 0
    )


def project_attachment_bytes(*, project: Project) -> int:
    """Return active attachment bytes for a project."""
    return (
        Attachment.objects.filter(deleted_at__isnull=True)
        .filter(project_attachment_filter(project))
        .aggregate(total=Sum("size_bytes"))["total"]
        or 0
    )


def project_for_parent(parent: Task | TaskComment) -> Project:
    """Return the project that owns an attachment parent."""
    if isinstance(parent, Task):
        return parent.project
    return parent.task.project


def raise_quota_exceeded(detail: str) -> None:
    """Raise an attachment quota error."""
    raise DomainError(
        code="attachment_quota_exceeded",
        detail=detail,
        status_code=HTTPStatus.BAD_REQUEST,
    )


def raise_permission_denied() -> None:
    """Raise a permission-denied domain error."""
    raise DomainError(
        code="permission_denied",
        detail="You do not have permission to perform this action.",
        status_code=HTTPStatus.FORBIDDEN,
    )
