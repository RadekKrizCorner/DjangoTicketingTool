"""Admin registrations for task models."""

from django.contrib import admin

from apps.tasks.models import Task, TaskComment


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
