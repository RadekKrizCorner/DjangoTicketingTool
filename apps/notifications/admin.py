"""Admin registrations for notification models."""

from django.contrib import admin

from apps.notifications.models import EmailDelivery, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for notifications."""

    list_display = ("type", "user", "project", "task", "read_at", "created_at")
    list_filter = ("type", "read_at", "created_at")
    search_fields = ("title", "message", "user__email", "dedupe_key")


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    """Admin configuration for email deliveries."""

    list_display = ("email", "status", "notification", "created_at", "sent_at")
    list_filter = ("status", "created_at", "sent_at")
    search_fields = ("email", "subject", "body", "error_message")
