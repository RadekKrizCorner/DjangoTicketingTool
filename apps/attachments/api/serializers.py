"""Serializers for attachment API endpoints."""

from rest_framework import serializers


class AttachmentOutputSerializer(serializers.Serializer):
    """Serialize attachment output."""

    id = serializers.IntegerField()
    task_id = serializers.IntegerField(allow_null=True)
    comment_id = serializers.IntegerField(allow_null=True)
    uploaded_by_id = serializers.IntegerField()
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    checksum_sha256 = serializers.CharField()
    created_at = serializers.DateTimeField()


class AttachmentEnvelopeSerializer(serializers.Serializer):
    """Serialize an attachment data envelope."""

    data = AttachmentOutputSerializer()


class AttachmentPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated attachment envelope."""

    data = AttachmentOutputSerializer(many=True)


class AttachmentUploadInputSerializer(serializers.Serializer):
    """Validate attachment upload input."""

    file = serializers.FileField()
