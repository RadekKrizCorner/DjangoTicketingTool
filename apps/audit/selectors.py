"""Audit log query selectors."""

from django.db.models import QuerySet

from apps.audit.models import AuditLog


def project_audit_logs(*, project) -> QuerySet[AuditLog]:
    """Return audit logs for a project ordered newest first."""
    return AuditLog.objects.filter(project=project).select_related("actor").order_by(
        "-created_at",
        "-id",
    )
