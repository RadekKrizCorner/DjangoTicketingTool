"""Project API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.projects.api.views import (
    ProjectAuditLogView,
    ProjectCloseScheduleView,
    ProjectCloseView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListCreateView,
    ProjectOwnershipTransferView,
    ProjectPublishScheduleView,
    ProjectReopenView,
)

urlpatterns: list[URLPattern] = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<int:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "<int:project_id>/ownership-transfer/",
        ProjectOwnershipTransferView.as_view(),
        name="project-ownership-transfer",
    ),
    path("<int:project_id>/close/", ProjectCloseView.as_view(), name="project-close"),
    path("<int:project_id>/reopen/", ProjectReopenView.as_view(), name="project-reopen"),
    path(
        "<int:project_id>/publish-schedule/",
        ProjectPublishScheduleView.as_view(),
        name="project-publish-schedule",
    ),
    path(
        "<int:project_id>/close-schedule/",
        ProjectCloseScheduleView.as_view(),
        name="project-close-schedule",
    ),
    path("<int:project_id>/audit-log/", ProjectAuditLogView.as_view(), name="project-audit-log"),
    path(
        "<int:project_id>/members/", ProjectMemberListCreateView.as_view(), name="project-members"
    ),
    path(
        "<int:project_id>/members/<int:membership_id>/",
        ProjectMemberDetailView.as_view(),
        name="project-member-detail",
    ),
]
