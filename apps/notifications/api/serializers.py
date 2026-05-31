"""Serializers for notification API endpoints."""

from rest_framework import serializers


class NotificationOutputSerializer(serializers.Serializer):
    """Serialize notification output."""

    id = serializers.IntegerField()
    type = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    project_id = serializers.IntegerField(allow_null=True)
    task_id = serializers.IntegerField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class NotificationEnvelopeSerializer(serializers.Serializer):
    """Serialize a notification data envelope."""

    data = NotificationOutputSerializer()


class NotificationPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated notification envelope."""

    data = NotificationOutputSerializer(many=True)


class NotificationStatusOutputSerializer(serializers.Serializer):
    """Serialize notification status output."""

    status = serializers.CharField()
    count = serializers.IntegerField(required=False)


class NotificationStatusEnvelopeSerializer(serializers.Serializer):
    """Serialize notification status envelope."""

    data = NotificationStatusOutputSerializer()
