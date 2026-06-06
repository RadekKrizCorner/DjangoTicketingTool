"""Serializers for task API endpoints."""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSummarySerializer
from apps.tasks import selectors
from apps.tasks.api import capabilities
from apps.tasks.models import Task


class PaginationMetaSerializer(serializers.Serializer):
    """Serialize response metadata."""

    pagination = serializers.DictField()


class TaskOutputSerializer(serializers.Serializer):
    """Serialize task output."""

    id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    project = serializers.SerializerMethodField()
    title = serializers.CharField()
    description = serializers.CharField()
    assignee_id = serializers.IntegerField()
    assignee = UserSummarySerializer()
    status = serializers.ChoiceField(choices=Task.Status.choices)
    priority = serializers.ChoiceField(choices=Task.Priority.choices)
    due_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    watched = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    def get_project(self, obj: Task) -> dict:
        """Return a small project summary."""
        return {
            "id": obj.project_id,
            "name": obj.project.name,
            "state": obj.project.state,
            "visibility": obj.project.visibility,
        }

    def get_watched(self, obj: Task) -> bool:
        """Return whether the context user watches the task."""
        return self._watched(obj)

    def get_allowed_transitions(self, obj: Task) -> list[str]:
        """Return allowed workflow transitions for the context user."""
        return capabilities.task_allowed_transitions(
            user=self.context.get("user"),
            task=obj,
            membership=self._membership(obj),
        )

    def get_capabilities(self, obj: Task) -> dict[str, bool]:
        """Return task capabilities for the context user."""
        return capabilities.task_capabilities(
            user=self.context.get("user"),
            task=obj,
            membership=self._membership(obj),
            watched=self._watched(obj),
        )

    def _membership(self, obj: Task):
        """Return cached project membership for the context user."""
        membership_map = self.context.get("membership_map")
        if membership_map is not None:
            return membership_map.get(obj.project_id)
        cache = self.context.setdefault("membership_cache", {})
        if obj.project_id not in cache:
            cache[obj.project_id] = capabilities.membership_for_task(
                user=self.context.get("user"),
                task=obj,
            )
        return cache[obj.project_id]

    def _watched(self, obj: Task) -> bool:
        """Return cached watcher status for the context user."""
        user = self.context.get("user")
        if user is None:
            return False
        watched_task_ids = self.context.get("watched_task_ids")
        if watched_task_ids is not None:
            return obj.id in watched_task_ids
        cache = self.context.setdefault("watched_cache", {})
        if obj.id not in cache:
            cache[obj.id] = selectors.task_is_watched_by_user(task=obj, user=user)
        return cache[obj.id]


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
    author = UserSummarySerializer()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj) -> dict[str, bool]:
        """Return comment capabilities for the context user."""
        membership = self.context.get("membership_map", {}).get(obj.task.project_id)
        if membership is None:
            membership = capabilities.membership_for_task(
                user=self.context.get("user"),
                task=obj.task,
            )
        return capabilities.comment_capabilities(
            user=self.context.get("user"),
            comment=obj,
            membership=membership,
        )


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
