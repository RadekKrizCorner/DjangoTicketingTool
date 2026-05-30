"""Audit log business services."""

from typing import Any

from apps.audit.models import AuditLog


def record_audit_log(
    *,
    actor: Any = None,
    action: str,
    entity_type: str,
    entity_id: int,
    project: Any = None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
    idempotency_key: str = "",
) -> AuditLog:
    """Create and return an audit log entry."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", True) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project=project,
        before=before or {},
        after=after or {},
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
        idempotency_key=idempotency_key,
    )
