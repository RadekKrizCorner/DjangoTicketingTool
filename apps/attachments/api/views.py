"""Views for attachment API endpoints."""

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import StandardPageNumberPagination
from apps.api.responses import success_response
from apps.attachments import selectors, services
from apps.attachments.api.serializers import (
    AttachmentLimitsEnvelopeSerializer,
    AttachmentOutputSerializer,
    AttachmentUploadInputSerializer,
)
from apps.projects import selectors as project_selectors
from apps.tasks import selectors as task_selectors


class TaskAttachmentListCreateView(APIView):
    """List and upload task attachments."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "upload"

    def get(self, request: Request, project_id: int, task_id: int) -> Response:
        """Return attachments for a visible task."""
        task, membership = visible_task_with_membership(
            request=request,
            project_id=project_id,
            task_id=task_id,
        )
        attachments = selectors.attachments_for_task(task=task)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(attachments, request, view=self)
        serializer = AttachmentOutputSerializer(
            page,
            many=True,
            context=attachment_serializer_context(
                user=request.user,
                attachments=page,
                project=task.project,
                membership=membership,
            ),
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int, task_id: int) -> Response:
        """Upload an attachment to a task."""
        task, membership = visible_task_with_membership(
            request=request,
            project_id=project_id,
            task_id=task_id,
        )
        serializer = AttachmentUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = services.create_attachment(
            actor=request.user,
            parent=task,
            uploaded_file=serializer.validated_data["file"],
        )
        return success_response(
            AttachmentOutputSerializer(
                attachment,
                context=attachment_serializer_context(
                    user=request.user,
                    attachments=[attachment],
                    project=task.project,
                    membership=membership,
                ),
            ).data,
            status_code=status.HTTP_201_CREATED,
        )


class CommentAttachmentListCreateView(APIView):
    """List and upload comment attachments."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "upload"

    def get(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Return attachments for a visible comment."""
        comment, membership = visible_comment_with_membership(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        attachments = selectors.attachments_for_comment(comment=comment)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(attachments, request, view=self)
        serializer = AttachmentOutputSerializer(
            page,
            many=True,
            context=attachment_serializer_context(
                user=request.user,
                attachments=page,
                project=comment.task.project,
                membership=membership,
            ),
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Upload an attachment to a comment."""
        comment, membership = visible_comment_with_membership(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        serializer = AttachmentUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = services.create_attachment(
            actor=request.user,
            parent=comment,
            uploaded_file=serializer.validated_data["file"],
        )
        return success_response(
            AttachmentOutputSerializer(
                attachment,
                context=attachment_serializer_context(
                    user=request.user,
                    attachments=[attachment],
                    project=comment.task.project,
                    membership=membership,
                ),
            ).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProjectAttachmentLimitsView(APIView):
    """Return attachment limits and usage for one project."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: AttachmentLimitsEnvelopeSerializer})
    def get(self, request: Request, project_id: int) -> Response:
        """Return upload limits and project attachment usage."""
        project = project_selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
        )
        project_used_bytes = services.project_attachment_bytes(project=project)
        max_project_bytes = settings.ATTACHMENT_MAX_PROJECT_BYTES
        return success_response(
            {
                "allowed_content_types": sorted(services.ALLOWED_CONTENT_TYPES),
                "allowed_text_extensions": sorted(services.TEXT_EXTENSIONS),
                "max_file_size_bytes": settings.ATTACHMENT_MAX_FILE_SIZE_BYTES,
                "max_project_bytes": max_project_bytes,
                "project_used_bytes": project_used_bytes,
                "project_remaining_bytes": max(max_project_bytes - project_used_bytes, 0),
            }
        )


class AttachmentDownloadView(APIView):
    """Download authorized attachments."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, attachment_id: int) -> HttpResponse:
        """Return attachment bytes after authorization."""
        attachment = selectors.attachment_or_404(attachment_id=attachment_id)
        if not selectors.can_read_attachment(user=request.user, attachment=attachment):
            project_selectors.raise_not_found()
        with attachment.file.open("rb") as file_obj:
            content = file_obj.read()
        response = HttpResponse(content, content_type=attachment.content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="{attachment.original_filename}"'
        )
        return response


class AttachmentDetailView(APIView):
    """Delete attachments."""

    permission_classes = (IsAuthenticated,)

    def delete(self, request: Request, attachment_id: int) -> Response:
        """Soft delete an attachment."""
        attachment = selectors.attachment_or_404(attachment_id=attachment_id)
        services.soft_delete_attachment(actor=request.user, attachment=attachment)
        return Response(status=status.HTTP_204_NO_CONTENT)


def visible_task(*, request: Request, project_id: int, task_id: int):
    """Return a task visible to the request user."""
    task, _membership = visible_task_with_membership(
        request=request,
        project_id=project_id,
        task_id=task_id,
    )
    return task


def visible_task_with_membership(*, request: Request, project_id: int, task_id: int):
    """Return a visible task and request user's project membership."""
    project = project_selectors.project_for_user_or_404(
        user=request.user,
        project_id=project_id,
    )
    membership = project_selectors.membership_for_user(project=project, user=request.user)
    task = task_selectors.task_for_user_or_404(
        user=request.user,
        project=project,
        task_id=task_id,
        membership=membership,
    )
    return task, membership


def visible_comment(*, request: Request, project_id: int, task_id: int, comment_id: int):
    """Return a comment visible to the request user."""
    comment, _membership = visible_comment_with_membership(
        request=request,
        project_id=project_id,
        task_id=task_id,
        comment_id=comment_id,
    )
    return comment


def visible_comment_with_membership(
    *,
    request: Request,
    project_id: int,
    task_id: int,
    comment_id: int,
):
    """Return a visible comment and request user's project membership."""
    task, membership = visible_task_with_membership(
        request=request,
        project_id=project_id,
        task_id=task_id,
    )
    return task_selectors.comment_for_task_or_404(task=task, comment_id=comment_id), membership


def attachment_serializer_context(*, user, attachments, project, membership=None) -> dict:
    """Return serializer context for attachment UI fields."""
    attachment_list = list(attachments)
    if membership is None:
        membership = project_selectors.membership_for_user(project=project, user=user)
    return {
        "user": user,
        "attachment_project_map": {attachment.id: project for attachment in attachment_list},
        "membership_map": {project.id: membership} if membership else {},
        "readable_attachment_ids": {attachment.id for attachment in attachment_list},
    }
