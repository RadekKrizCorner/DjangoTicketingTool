"""Dashboard admin configuration."""

from django.contrib import admin

from apps.dashboards.models import Dashboard, DashboardShare, DashboardWidget


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    """Admin configuration for dashboards."""

    list_display = ("name", "owner", "created_at", "deleted_at")
    search_fields = ("name", "owner__email", "owner__display_name")
    list_filter = ("deleted_at", "created_at")


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    """Admin configuration for dashboard widgets."""

    list_display = ("title", "dashboard", "type", "order", "deleted_at")
    list_filter = ("type", "deleted_at")
    search_fields = ("title", "dashboard__name")


@admin.register(DashboardShare)
class DashboardShareAdmin(admin.ModelAdmin):
    """Admin configuration for dashboard shares."""

    list_display = ("dashboard", "target_type", "user", "project", "access", "deleted_at")
    list_filter = ("target_type", "access", "deleted_at")
