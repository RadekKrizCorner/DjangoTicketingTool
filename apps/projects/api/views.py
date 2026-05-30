"""Views for project API endpoints."""

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
from apps.projects import selectors, services
from apps.projects.api.serializers import (
    AuditLogOutputSerializer,
    AuditLogPaginatedEnvelopeSerializer,
    CloseScheduleInputSerializer,
    OwnershipTransferInputSerializer,
    ProjectCreateInputSerializer,
    ProjectEnvelopeSerializer,
    ProjectMembershipEnvelopeSerializer,
    ProjectMembershipInputSerializer,
    ProjectMembershipOutputSerializer,
    ProjectMembershipPaginatedEnvelopeSerializer,
    ProjectMembershipUpdateInputSerializer,
    ProjectOutputSerializer,
    ProjectPaginatedEnvelopeSerializer,
    ProjectUpdateInputSerializer,
    PublishScheduleInputSerializer,
)


class ProjectListCreateView(APIView):
    """List and create projects."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_list",
        responses={200: ProjectPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        """Return projects visible to the authenticated user."""
        projects = selectors.filter_visible_projects(
            user=request.user,
            visibility=request.query_params.get("visibility"),
            role=request.query_params.get("role"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering"),
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(projects, request, view=self)
        serializer = ProjectOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="projects_create",
        request=ProjectCreateInputSerializer,
        responses={201: ProjectEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Create a project owned by the authenticated user."""
        serializer = ProjectCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = services.create_project(actor=request.user, data=serializer.validated_data)
        return success_response(
            ProjectOutputSerializer(project).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    """Read, update, and delete a project."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="projects_retrieve", responses={200: ProjectEnvelopeSerializer})
    def get(self, request: Request, project_id: int) -> Response:
        """Return one visible project."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        return success_response(ProjectOutputSerializer(project).data)

    @extend_schema(
        operation_id="projects_partial_update",
        request=ProjectUpdateInputSerializer,
        responses={200: ProjectEnvelopeSerializer},
    )
    def patch(self, request: Request, project_id: int) -> Response:
        """Update owner-managed project fields."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        serializer = ProjectUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_project = services.update_project(
            actor=request.user,
            project=project,
            data=serializer.validated_data,
        )
        return success_response(ProjectOutputSerializer(updated_project).data)

    @extend_schema(operation_id="projects_destroy", responses={204: None})
    def delete(self, request: Request, project_id: int) -> Response:
        """Soft delete a project."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        services.soft_delete_project(actor=request.user, project=project)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectOwnershipTransferView(APIView):
    """Transfer project ownership."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_ownership_transfer",
        request=OwnershipTransferInputSerializer,
        responses={200: ProjectEnvelopeSerializer},
    )
    def post(self, request: Request, project_id: int) -> Response:
        """Transfer ownership to another active user."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        serializer = OwnershipTransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_owner = get_active_user_or_400(serializer.validated_data["new_owner_id"])
        updated_project = services.transfer_project_ownership(
            actor=request.user,
            project=project,
            new_owner=new_owner,
        )
        return success_response(ProjectOutputSerializer(updated_project).data)


class ProjectCloseView(APIView):
    """Close projects."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_close",
        request=None,
        responses={200: ProjectEnvelopeSerializer},
    )
    def post(self, request: Request, project_id: int) -> Response:
        """Close an active project."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        closed_project = services.close_project(actor=request.user, project=project)
        return success_response(ProjectOutputSerializer(closed_project).data)


class ProjectReopenView(APIView):
    """Reopen projects."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_reopen",
        request=None,
        responses={200: ProjectEnvelopeSerializer},
    )
    def post(self, request: Request, project_id: int) -> Response:
        """Reopen a closed project."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        reopened_project = services.reopen_project(actor=request.user, project=project)
        return success_response(ProjectOutputSerializer(reopened_project).data)


class ProjectPublishScheduleView(APIView):
    """Manage project publish schedules."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_publish_schedule_update",
        request=PublishScheduleInputSerializer,
        responses={200: ProjectEnvelopeSerializer},
    )
    def put(self, request: Request, project_id: int) -> Response:
        """Set a project publish schedule."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        serializer = PublishScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheduled_project = services.schedule_publish(
            actor=request.user,
            project=project,
            publish_at=serializer.validated_data["publish_at"],
        )
        return success_response(ProjectOutputSerializer(scheduled_project).data)

    @extend_schema(
        operation_id="projects_publish_schedule_destroy",
        responses={204: None},
    )
    def delete(self, request: Request, project_id: int) -> Response:
        """Cancel a project publish schedule."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        services.cancel_publish_schedule(actor=request.user, project=project)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCloseScheduleView(APIView):
    """Manage project close schedules."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_close_schedule_update",
        request=CloseScheduleInputSerializer,
        responses={200: ProjectEnvelopeSerializer},
    )
    def put(self, request: Request, project_id: int) -> Response:
        """Set a project close schedule."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        serializer = CloseScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheduled_project = services.schedule_close(
            actor=request.user,
            project=project,
            close_at=serializer.validated_data["close_at"],
        )
        return success_response(ProjectOutputSerializer(scheduled_project).data)

    @extend_schema(
        operation_id="projects_close_schedule_destroy",
        responses={204: None},
    )
    def delete(self, request: Request, project_id: int) -> Response:
        """Cancel a project close schedule."""
        project = selectors.project_for_user_or_404(
            user=request.user,
            project_id=project_id,
            allow_staff=True,
        )
        services.cancel_close_schedule(actor=request.user, project=project)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectAuditLogView(APIView):
    """Read project audit logs."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_audit_log_list",
        responses={200: AuditLogPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request, project_id: int) -> Response:
        """Return project audit logs for project owners."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        audit_logs = selectors.project_audit_logs_for_user_or_403(
            project=project,
            user=request.user,
        )
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(audit_logs, request, view=self)
        serializer = AuditLogOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProjectMemberListCreateView(APIView):
    """List and create project memberships."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_members_list",
        responses={200: ProjectMembershipPaginatedEnvelopeSerializer},
    )
    def get(self, request: Request, project_id: int) -> Response:
        """Return active memberships for a visible project."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        memberships = selectors.project_memberships(project=project)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(memberships, request, view=self)
        serializer = ProjectMembershipOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="projects_members_create",
        request=ProjectMembershipInputSerializer,
        responses={201: ProjectMembershipEnvelopeSerializer},
    )
    def post(self, request: Request, project_id: int) -> Response:
        """Add a project membership."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        serializer = ProjectMembershipInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_active_user_or_400(serializer.validated_data["user_id"])
        membership = services.add_project_member(
            actor=request.user,
            project=project,
            user=user,
            role=serializer.validated_data["role"],
        )
        return success_response(
            ProjectMembershipOutputSerializer(membership).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProjectMemberDetailView(APIView):
    """Read, update, and delete project memberships."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="projects_members_retrieve",
        responses={200: ProjectMembershipEnvelopeSerializer},
    )
    def get(self, request: Request, project_id: int, membership_id: int) -> Response:
        """Return one active project membership."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        membership = selectors.membership_or_404(project=project, membership_id=membership_id)
        return success_response(ProjectMembershipOutputSerializer(membership).data)

    @extend_schema(
        operation_id="projects_members_partial_update",
        request=ProjectMembershipUpdateInputSerializer,
        responses={200: ProjectMembershipEnvelopeSerializer},
    )
    def patch(self, request: Request, project_id: int, membership_id: int) -> Response:
        """Update a project membership role."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        membership = selectors.membership_or_404(project=project, membership_id=membership_id)
        serializer = ProjectMembershipUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_membership = services.update_project_member(
            actor=request.user,
            project=project,
            membership=membership,
            role=serializer.validated_data["role"],
        )
        return success_response(ProjectMembershipOutputSerializer(updated_membership).data)

    @extend_schema(operation_id="projects_members_destroy", responses={204: None})
    def delete(self, request: Request, project_id: int, membership_id: int) -> Response:
        """Soft delete a project membership."""
        project = selectors.project_for_user_or_404(user=request.user, project_id=project_id)
        membership = selectors.membership_or_404(project=project, membership_id=membership_id)
        services.remove_project_member(actor=request.user, project=project, membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


def get_active_user_or_400(user_id: int):
    """Return an active user or raise a validation error."""
    User = get_user_model()
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise DomainError(
            code="validation_error",
            detail="Active user was not found.",
            field="user_id",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return user
