"""Admin registrations for task models."""

from django.contrib import admin

from apps.tasks.models import Task, TaskComment, TaskWatcher


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin configuration for tasks."""

    list_display = ("title", "project", "assignee", "status", "priority", "due_at")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description", "assignee__email")


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """Admin configuration for task comments."""

    list_display = ("task", "author", "created_at", "deleted_at")
    search_fields = ("body", "author__email", "task__title")


@admin.register(TaskWatcher)
class TaskWatcherAdmin(admin.ModelAdmin):
    """Admin configuration for task watchers."""

    list_display = ("task", "user", "created_at", "deleted_at")
    list_filter = ("deleted_at",)
    search_fields = ("task__title", "user__email")
