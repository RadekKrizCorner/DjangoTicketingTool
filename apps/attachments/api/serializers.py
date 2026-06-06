"""Serializers for attachment API endpoints."""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSummarySerializer


class AttachmentOutputSerializer(serializers.Serializer):
    """Serialize attachment output."""

    id = serializers.IntegerField()
    task_id = serializers.IntegerField(allow_null=True)
    comment_id = serializers.IntegerField(allow_null=True)
    uploaded_by_id = serializers.IntegerField()
    uploaded_by = UserSummarySerializer()
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    checksum_sha256 = serializers.CharField()
    created_at = serializers.DateTimeField()
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj) -> dict[str, bool]:
        """Return attachment capabilities for the context user."""
        from apps.attachments.api.capabilities import attachment_capabilities_for_context

        project = self.context.get("attachment_project_map", {}).get(obj.id)
        readable_ids = self.context.get("readable_attachment_ids")
        return attachment_capabilities_for_context(
            user=self.context.get("user"),
            attachment=obj,
            project=project,
            membership=self.context.get("membership_map", {}).get(project.id) if project else None,
            can_download=obj.id in readable_ids if readable_ids is not None else None,
        )


class AttachmentEnvelopeSerializer(serializers.Serializer):
    """Serialize an attachment data envelope."""

    data = AttachmentOutputSerializer()


class AttachmentPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated attachment envelope."""

    data = AttachmentOutputSerializer(many=True)


class AttachmentUploadInputSerializer(serializers.Serializer):
    """Validate attachment upload input."""

    file = serializers.FileField()


class AttachmentLimitsOutputSerializer(serializers.Serializer):
    """Serialize attachment limit output."""

    allowed_content_types = serializers.ListField(child=serializers.CharField())
    allowed_text_extensions = serializers.ListField(child=serializers.CharField())
    max_file_size_bytes = serializers.IntegerField()
    max_project_bytes = serializers.IntegerField()
    project_used_bytes = serializers.IntegerField()
    project_remaining_bytes = serializers.IntegerField()


class AttachmentLimitsEnvelopeSerializer(serializers.Serializer):
    """Serialize attachment limits data envelope."""

    data = AttachmentLimitsOutputSerializer()
