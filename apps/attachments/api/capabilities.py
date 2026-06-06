"""UI capability helpers for attachment API output."""

from typing import Any

from apps.attachments import selectors
from apps.attachments.models import Attachment
from apps.projects import selectors as project_selectors
from apps.tasks import policies as task_policies


def attachment_capabilities(*, user: Any, attachment: Attachment) -> dict[str, bool]:
    """Return UI capabilities for one attachment."""
    return attachment_capabilities_for_context(
        user=user,
        attachment=attachment,
        project=None,
        membership=None,
        can_download=None,
    )


def attachment_capabilities_for_context(
    *,
    user: Any,
    attachment: Attachment,
    project,
    membership,
    can_download: bool | None,
) -> dict[str, bool]:
    """Return attachment capabilities using optional precomputed context."""
    if not getattr(user, "is_authenticated", False):
        return {
            "can_download": False,
            "can_delete": False,
        }
    if project is None:
        project = selectors.project_for_attachment(attachment)
    if membership is None:
        membership = project_selectors.membership_for_user(project=project, user=user)
    return {
        "can_download": (
            selectors.can_read_attachment(user=user, attachment=attachment)
            if can_download is None
            else can_download
        ),
        "can_delete": task_policies.can_delete_attachment(
            actor=user,
            membership=membership,
            uploaded_by_id=attachment.uploaded_by_id,
        ),
    }
