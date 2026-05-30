"""Admin registrations for project models."""

from django.contrib import admin

from apps.projects.models import Project, ProjectMembership

AUDIT_READONLY_FIELDS = (
    "created_at",
    "updated_at",
    "deleted_at",
    "created_by",
    "updated_by",
    "deleted_by",
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for projects."""

    list_display = ("id", "name", "owner", "visibility", "state", "deleted_at", "created_at")
    list_filter = ("visibility", "state", "deleted_at", "created_at")
    search_fields = ("name", "description", "owner__email", "owner__display_name")
    readonly_fields = AUDIT_READONLY_FIELDS
    autocomplete_fields = ("owner", "created_by", "updated_by", "deleted_by")

    def get_readonly_fields(self, request, obj=None):
        """Return read-only fields, protecting owner after creation."""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.append("owner")
        return tuple(dict.fromkeys(readonly_fields))

    def save_model(self, request, obj, form, change) -> None:
        """Save a project and create owner membership on admin creation."""
        super().save_model(request, obj, form, change)
        if change:
            return
        ProjectMembership.objects.get_or_create(
            project=obj,
            user=obj.owner,
            defaults={
                "role": ProjectMembership.Role.OWNER,
                "created_by": request.user,
                "updated_by": request.user,
            },
        )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for project memberships."""

    list_display = ("id", "project", "user", "role", "deleted_at", "created_at")
    list_filter = ("role", "deleted_at", "created_at")
    search_fields = ("project__name", "user__email", "user__display_name")
    readonly_fields = AUDIT_READONLY_FIELDS
    autocomplete_fields = ("project", "user", "created_by", "updated_by", "deleted_by")

    def get_readonly_fields(self, request, obj=None):
        """Return read-only fields, protecting active owner memberships."""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly_fields.extend(["project", "user"])
        if obj is not None and obj.deleted_at is None and obj.role == ProjectMembership.Role.OWNER:
            readonly_fields.append("role")
        return tuple(dict.fromkeys(readonly_fields))
