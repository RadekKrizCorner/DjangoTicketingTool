"""Views for task API endpoints."""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import StandardPageNumberPagination
from apps.api.responses import success_response
from apps.common.errors import DomainError
from apps.projects import selectors as project_selectors
from apps.projects.models import ProjectMembership
from apps.tasks import selectors, services
from apps.tasks.api import filters as task_filters
from apps.tasks.api.serializers import (
    TaskCommentInputSerializer,
    TaskCommentOutputSerializer,
    TaskCreateInputSerializer,
    TaskOutputSerializer,
    TaskPaginatedEnvelopeSerializer,
    TaskTransitionInputSerializer,
    TaskUpdateInputSerializer,
    TaskWatchStatusSerializer,
    task_service_data,
)
from apps.tasks.models import Task, TaskComment, TaskWatcher


class TaskListCreateView(APIView):
    """List and create project tasks."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=task_filters.TASK_FILTER_PARAMETERS,
        responses={200: TaskPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request, project_id: int) -> Response:
        """Return visible tasks for a project."""
        project = project_selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
        )
        membership = project_selectors.membership_for_user(project=project, user=request.user)
        tasks = task_filters.filtered_task_queryset(
            request=request,
            queryset=selectors.visible_tasks_for_project(
                user=request.user,
                project=project,
                membership=membership,
            ),
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        serializer = TaskOutputSerializer(
            page,
            many=True,
            context=task_serializer_context(
                user=request.user,
                tasks=page,
                membership_map={project.id: membership} if membership else {},
            ),
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int) -> Response:
        """Create a project task."""
        project = project_selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
        )
        serializer = TaskCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = task_service_data(serializer.validated_data)
        data["assignee"] = get_active_user_or_400(data["assignee"])
        task = services.create_task(actor=request.user, project=project, data=data)
        return success_response(
            TaskOutputSerializer(
                task,
                context=task_serializer_context(user=request.user, tasks=[task]),
            ).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskDetailView(APIView):
    """Read, update, and delete project tasks."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, project_id: int, task_id: int) -> Response:
        """Return one visible task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        return success_response(
            TaskOutputSerializer(
                task,
                context=task_serializer_context(user=request.user, tasks=[task]),
            ).data
        )

    def patch(self, request: Request, project_id: int, task_id: int) -> Response:
        """Update a task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        serializer = TaskUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = task_service_data(serializer.validated_data)
        if "assignee" in data:
            data["assignee"] = get_active_user_or_400(data["assignee"])
        updated_task = services.update_task(actor=request.user, task=task, data=data)
        return success_response(
            TaskOutputSerializer(
                updated_task,
                context=task_serializer_context(user=request.user, tasks=[updated_task]),
            ).data
        )

    def delete(self, request: Request, project_id: int, task_id: int) -> Response:
        """Soft delete a task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        services.soft_delete_task(actor=request.user, task=task)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskTransitionView(APIView):
    """Transition task workflow status."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, project_id: int, task_id: int) -> Response:
        """Move a task to a target status."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        serializer = TaskTransitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_task = services.transition_task(
            actor=request.user,
            task=task,
            target_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return success_response(
            TaskOutputSerializer(
                updated_task,
                context=task_serializer_context(user=request.user, tasks=[updated_task]),
            ).data
        )


class TaskWatchView(APIView):
    """Watch and unwatch a task."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, project_id: int, task_id: int) -> Response:
        """Subscribe the current user to a task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        services.watch_task(actor=request.user, task=task)
        serializer = TaskWatchStatusSerializer({"watched": True})
        return success_response(serializer.data)

    def delete(self, request: Request, project_id: int, task_id: int) -> Response:
        """Unsubscribe the current user from a task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        services.unwatch_task(actor=request.user, task=task)
        serializer = TaskWatchStatusSerializer({"watched": False})
        return success_response(serializer.data)


class TaskCommentListCreateView(APIView):
    """List and create task comments."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, project_id: int, task_id: int) -> Response:
        """Return comments for a visible task."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        comments = selectors.comments_for_task(task=task)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(comments, request, view=self)
        serializer = TaskCommentOutputSerializer(
            page,
            many=True,
            context=comment_serializer_context(user=request.user, comments=page),
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int, task_id: int) -> Response:
        """Create a task comment."""
        task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
        serializer = TaskCommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.create_comment(
            actor=request.user,
            task=task,
            body=serializer.validated_data["body"],
        )
        return success_response(
            TaskCommentOutputSerializer(
                comment,
                context=comment_serializer_context(user=request.user, comments=[comment]),
            ).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskCommentDetailView(APIView):
    """Read, update, and delete task comments."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Return one task comment."""
        comment = get_visible_comment(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        return success_response(
            TaskCommentOutputSerializer(
                comment,
                context=comment_serializer_context(user=request.user, comments=[comment]),
            ).data
        )

    def patch(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Update one task comment."""
        comment = get_visible_comment(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        serializer = TaskCommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_comment = services.update_comment(
            actor=request.user,
            comment=comment,
            body=serializer.validated_data["body"],
        )
        return success_response(
            TaskCommentOutputSerializer(
                updated_comment,
                context=comment_serializer_context(user=request.user, comments=[updated_comment]),
            ).data
        )

    def delete(
        self,
        request: Request,
        project_id: int,
        task_id: int,
        comment_id: int,
    ) -> Response:
        """Soft delete one task comment."""
        comment = get_visible_comment(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        services.soft_delete_comment(actor=request.user, comment=comment)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyTasksView(APIView):
    """List the current user's assigned tasks."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=task_filters.TASK_FILTER_PARAMETERS,
        responses={200: TaskPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        """Return tasks assigned to the current user."""
        tasks = task_filters.filtered_task_queryset(
            request=request,
            queryset=selectors.assigned_tasks_for_user(user=request.user),
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        serializer = TaskOutputSerializer(
            page,
            many=True,
            context=task_serializer_context(user=request.user, tasks=page),
        )
        return paginator.get_paginated_response(serializer.data)


class DueSoonTasksView(APIView):
    """List the current user's tasks due soon."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=task_filters.TASK_FILTER_PARAMETERS,
        responses={200: TaskPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        """Return tasks due in the next day."""
        tasks = task_filters.filtered_task_queryset(
            request=request,
            queryset=selectors.due_soon_tasks_for_user(user=request.user),
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        serializer = TaskOutputSerializer(
            page,
            many=True,
            context=task_serializer_context(user=request.user, tasks=page),
        )
        return paginator.get_paginated_response(serializer.data)


def get_visible_task(*, request: Request, project_id: int, task_id: int):
    """Return a task visible to the request user."""
    task, _membership = get_visible_task_with_membership(
        request=request,
        project_id=project_id,
        task_id=task_id,
    )
    return task


def get_visible_task_with_membership(*, request: Request, project_id: int, task_id: int):
    """Return a task and membership visible to the request user."""
    project = project_selectors.project_for_user_or_404(
        user=request.user,
        project_id=project_id,
    )
    membership = project_selectors.membership_for_user(project=project, user=request.user)
    task = selectors.task_for_user_or_404(
        user=request.user,
        project=project,
        task_id=task_id,
        membership=membership,
    )
    return task, membership


def get_visible_comment(*, request: Request, project_id: int, task_id: int, comment_id: int):
    """Return a comment visible to the request user."""
    task = get_visible_task(request=request, project_id=project_id, task_id=task_id)
    return selectors.comment_for_task_or_404(task=task, comment_id=comment_id)


def get_active_user_or_400(user_id: int):
    """Return an active user or raise a validation error."""
    User = get_user_model()
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise DomainError(
            code="validation_error",
            detail="Active user was not found.",
            field="assignee_id",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return user


def task_serializer_context(*, user, tasks: list[Task], membership_map: dict | None = None) -> dict:
    """Return serializer context for task UI fields."""
    task_list = list(tasks)
    project_ids = {task.project_id for task in task_list}
    task_ids = {task.id for task in task_list}
    if membership_map is None:
        memberships = ProjectMembership.objects.filter(
            deleted_at__isnull=True,
            project__deleted_at__isnull=True,
            user=user,
            project_id__in=project_ids,
        )
        membership_map = {membership.project_id: membership for membership in memberships}
    watched_task_ids = set(
        TaskWatcher.objects.filter(
            deleted_at__isnull=True,
            user=user,
            task_id__in=task_ids,
            task__project__memberships__user=user,
            task__project__memberships__deleted_at__isnull=True,
        ).values_list("task_id", flat=True)
    )
    return {
        "user": user,
        "membership_map": membership_map,
        "watched_task_ids": watched_task_ids,
    }


def comment_serializer_context(*, user, comments: list[TaskComment]) -> dict:
    """Return serializer context for comment UI fields."""
    comment_list = list(comments)
    project_ids = {comment.task.project_id for comment in comment_list}
    memberships = ProjectMembership.objects.filter(
        deleted_at__isnull=True,
        project__deleted_at__isnull=True,
        user=user,
        project_id__in=project_ids,
    )
    return {
        "user": user,
        "membership_map": {membership.project_id: membership for membership in memberships},
    }
