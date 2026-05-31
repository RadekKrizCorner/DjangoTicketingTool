"""Admin registrations for attachment models."""

from django.contrib import admin

from apps.attachments.models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for attachments."""

    list_display = ("original_filename", "uploaded_by", "content_type", "size_bytes", "created_at")
    list_filter = ("content_type", "created_at", "deleted_at")
    search_fields = ("original_filename", "uploaded_by__email", "checksum_sha256")
