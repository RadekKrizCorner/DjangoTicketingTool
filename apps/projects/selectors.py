"""Project query selectors."""

from http import HTTPStatus
from typing import Any

from django.db.models import Q, QuerySet

from apps.audit import selectors as audit_selectors
from apps.common.errors import DomainError
from apps.projects.models import Project, ProjectMembership
from apps.projects.policies import can_read_audit_log

PROJECT_ORDERING_FIELDS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "name": "name",
    "-name": "-name",
    "visibility": "visibility",
    "-visibility": "-visibility",
    "state": "state",
    "-state": "-state",
}


def non_deleted_projects() -> QuerySet[Project]:
    """Return projects that have not been soft deleted."""
    return Project.objects.filter(deleted_at__isnull=True).select_related("owner")


def active_memberships() -> QuerySet[ProjectMembership]:
    """Return memberships that have not been soft deleted."""
    return ProjectMembership.objects.filter(
        deleted_at__isnull=True,
        project__deleted_at__isnull=True,
    ).select_related("project", "user")


def visible_projects_for_user(user: Any) -> QuerySet[Project]:
    """Return projects visible to an authenticated user."""
    if not getattr(user, "is_authenticated", False):
        return Project.objects.none()

    return (
        non_deleted_projects()
        .filter(
            Q(visibility=Project.Visibility.PUBLIC)
            | Q(memberships__user=user, memberships__deleted_at__isnull=True)
        )
        .distinct()
        .order_by("-created_at", "-id")
    )


def filter_visible_projects(
    *,
    user: Any,
    visibility: str | None = None,
    role: str | None = None,
    search: str | None = None,
    ordering: str | None = None,
) -> QuerySet[Project]:
    """Return visible projects with supported filters applied."""
    projects = visible_projects_for_user(user)
    if visibility:
        projects = projects.filter(visibility=visibility)
    if role:
        projects = projects.filter(
            memberships__user=user,
            memberships__role=role,
            memberships__deleted_at__isnull=True,
        )
    normalized_search = (search or "").strip()
    if normalized_search:
        projects = projects.filter(
            Q(name__icontains=normalized_search) | Q(description__icontains=normalized_search)
        )

    ordering_field = PROJECT_ORDERING_FIELDS.get(ordering or "", "-created_at")
    secondary_ordering = "id" if not ordering_field.startswith("-") else "-id"
    return projects.distinct().order_by(ordering_field, secondary_ordering)


def project_for_user_or_404(
    *,
    user: Any,
    project_id: int,
    allow_staff: bool = False,
) -> Project:
    """Return a visible project or raise a not-found domain error."""
    if allow_staff and getattr(user, "is_staff", False) and getattr(user, "is_active", False):
        project = non_deleted_projects().filter(pk=project_id).first()
    else:
        project = visible_projects_for_user(user).filter(pk=project_id).first()
    if project is None:
        raise_not_found()
    return project


def membership_for_user(
    *,
    project: Project,
    user: Any,
) -> ProjectMembership | None:
    """Return the active membership for a user in a project."""
    if not getattr(user, "is_authenticated", False):
        return None
    return active_memberships().filter(project=project, user=user).first()


def project_memberships(*, project: Project) -> QuerySet[ProjectMembership]:
    """Return active memberships for a project."""
    return active_memberships().filter(project=project).order_by("created_at", "id")


def membership_or_404(*, project: Project, membership_id: int) -> ProjectMembership:
    """Return an active project membership or raise not found."""
    membership = active_memberships().filter(project=project, pk=membership_id).first()
    if membership is None:
        raise_not_found()
    return membership


def project_audit_logs_for_user_or_403(*, project: Project, user: Any) -> QuerySet:
    """Return project audit logs when the user is the owner."""
    membership = membership_for_user(project=project, user=user)
    if not can_read_audit_log(actor=user, project=project, membership=membership):
        raise DomainError(
            code="permission_denied",
            detail="You do not have permission to read this project audit log.",
            status_code=HTTPStatus.FORBIDDEN,
        )
    return audit_selectors.project_audit_logs(project=project)


def raise_not_found() -> None:
    """Raise the standard project not-found error."""
    raise DomainError(
        code="not_found",
        detail="Project was not found.",
        status_code=HTTPStatus.NOT_FOUND,
    )
