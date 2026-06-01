"""Serializers for task API endpoints."""

from rest_framework import serializers

from apps.tasks import selectors
from apps.tasks.models import Task


class PaginationMetaSerializer(serializers.Serializer):
    """Serialize response metadata."""

    pagination = serializers.DictField()


class TaskOutputSerializer(serializers.Serializer):
    """Serialize task output."""

    id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    assignee_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Task.Status.choices)
    priority = serializers.ChoiceField(choices=Task.Priority.choices)
    due_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    watched = serializers.SerializerMethodField()

    def get_watched(self, obj: Task) -> bool:
        """Return whether the context user watches the task."""
        user = self.context.get("user")
        if user is None:
            return False
        return selectors.task_is_watched_by_user(task=obj, user=user)


class TaskEnvelopeSerializer(serializers.Serializer):
    """Serialize a task data envelope."""

    data = TaskOutputSerializer()


class TaskPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated task envelope."""

    data = TaskOutputSerializer(many=True)
    meta = PaginationMetaSerializer()


class TaskCreateInputSerializer(serializers.Serializer):
    """Validate task creation input."""

    title = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    assignee_id = serializers.IntegerField()
    priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
        default=Task.Priority.MEDIUM,
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class TaskUpdateInputSerializer(serializers.Serializer):
    """Validate task update input."""

    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    assignee_id = serializers.IntegerField(required=False)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False)
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class TaskTransitionInputSerializer(serializers.Serializer):
    """Validate task transition input."""

    status = serializers.ChoiceField(choices=Task.Status.choices)
    note = serializers.CharField(allow_blank=True, required=False, default="")


class TaskCommentOutputSerializer(serializers.Serializer):
    """Serialize task comment output."""

    id = serializers.IntegerField()
    task_id = serializers.IntegerField()
    author_id = serializers.IntegerField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class TaskCommentEnvelopeSerializer(serializers.Serializer):
    """Serialize a task comment data envelope."""

    data = TaskCommentOutputSerializer()


class TaskCommentPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated task comment envelope."""

    data = TaskCommentOutputSerializer(many=True)
    meta = PaginationMetaSerializer()


class TaskCommentInputSerializer(serializers.Serializer):
    """Validate task comment input."""

    body = serializers.CharField()


class TaskWatchStatusSerializer(serializers.Serializer):
    """Serialize task watcher state."""

    watched = serializers.BooleanField()


def task_service_data(validated_data: dict) -> dict:
    """Map task serializer data to service data."""
    data = dict(validated_data)
    if "assignee_id" in data:
        data["assignee"] = data.pop("assignee_id")
    return data
