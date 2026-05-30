"""Admin registrations for audit models."""

from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for audit logs."""

    list_display = ("id", "action", "entity_type", "entity_id", "project", "actor", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = (
        "action",
        "entity_type",
        "entity_id",
        "project__name",
        "actor__email",
        "idempotency_key",
    )
    readonly_fields = (
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "project",
        "before",
        "after",
        "metadata",
        "ip_address",
        "user_agent",
        "idempotency_key",
        "created_at",
    )
