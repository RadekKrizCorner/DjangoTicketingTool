"""Views for attachment API endpoints."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import StandardPageNumberPagination
from apps.api.responses import success_response
from apps.attachments import selectors, services
from apps.attachments.api.serializers import (
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
        task = visible_task(request=request, project_id=project_id, task_id=task_id)
        attachments = selectors.attachments_for_task(task=task)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(attachments, request, view=self)
        serializer = AttachmentOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int, task_id: int) -> Response:
        """Upload an attachment to a task."""
        task = visible_task(request=request, project_id=project_id, task_id=task_id)
        serializer = AttachmentUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = services.create_attachment(
            actor=request.user,
            parent=task,
            uploaded_file=serializer.validated_data["file"],
        )
        return success_response(
            AttachmentOutputSerializer(attachment).data,
            status_code=status.HTTP_201_CREATED,
        )


class CommentAttachmentListCreateView(APIView):
    """List and upload comment attachments."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "upload"

    def get(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Return attachments for a visible comment."""
        comment = visible_comment(
            request=request,
            project_id=project_id,
            task_id=task_id,
            comment_id=comment_id,
        )
        attachments = selectors.attachments_for_comment(comment=comment)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(attachments, request, view=self)
        serializer = AttachmentOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request, project_id: int, task_id: int, comment_id: int) -> Response:
        """Upload an attachment to a comment."""
        comment = visible_comment(
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
            AttachmentOutputSerializer(attachment).data,
            status_code=status.HTTP_201_CREATED,
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
    project = project_selectors.project_for_user_or_404(
        user=request.user,
        project_id=project_id,
    )
    return task_selectors.task_for_user_or_404(
        user=request.user,
        project=project,
        task_id=task_id,
    )


def visible_comment(*, request: Request, project_id: int, task_id: int, comment_id: int):
    """Return a comment visible to the request user."""
    task = visible_task(request=request, project_id=project_id, task_id=task_id)
    return task_selectors.comment_for_task_or_404(task=task, comment_id=comment_id)
