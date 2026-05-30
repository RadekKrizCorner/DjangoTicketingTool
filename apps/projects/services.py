"""Project business services."""

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_audit_log
from apps.common.errors import DomainError
from apps.projects import policies, selectors
from apps.projects.models import Project, ProjectMembership

PROJECT_UPDATE_FIELDS = {"name", "description", "visibility", "public_comment_policy"}


def create_project(*, actor: Any, data: dict) -> Project:
    """Create a project with an owner membership and audit log."""
    with transaction.atomic():
        project = Project.objects.create(
            name=data["name"],
            description=data.get("description", ""),
            owner=actor,
            visibility=data.get("visibility", Project.Visibility.PRIVATE),
            public_comment_policy=data.get(
                "public_comment_policy",
                Project.PublicCommentPolicy.MEMBERS_ONLY,
            ),
            created_by=actor,
            updated_by=actor,
        )
        ProjectMembership.objects.create(
            project=project,
            user=actor,
            role=ProjectMembership.Role.OWNER,
            created_by=actor,
            updated_by=actor,
        )
        record_audit_log(
            actor=actor,
            action="project.created",
            entity_type="project",
            entity_id=project.id,
            project=project,
            after=project_snapshot(project),
        )
    return project


def update_project(*, actor: Any, project: Project, data: dict) -> Project:
    """Update owner-managed project fields and write an audit log."""
    update_data = {key: value for key, value in data.items() if key in PROJECT_UPDATE_FIELDS}

    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        if not update_data:
            return locked_project

        before = project_snapshot(locked_project)
        for field, value in update_data.items():
            setattr(locked_project, field, value)
        locked_project.updated_by = actor
        locked_project.save(update_fields=[*update_data, "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="project.updated",
            entity_type="project",
            entity_id=locked_project.id,
            project=locked_project,
            before=before,
            after=project_snapshot(locked_project),
        )
    return locked_project


def add_project_member(
    *,
    actor: Any,
    project: Project,
    user: Any,
    role: str,
) -> ProjectMembership:
    """Add or restore a project membership."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        if role == ProjectMembership.Role.OWNER:
            raise_invalid_role("Use ownership transfer to assign the owner role.")

        active_membership = selectors.membership_for_user(project=locked_project, user=user)
        if active_membership is not None:
            raise DomainError(
                code="duplicate_membership",
                detail="User already has an active project membership.",
                status_code=HTTPStatus.CONFLICT,
            )

        membership = soft_deleted_membership(project=locked_project, user=user)
        if membership is None:
            try:
                membership = ProjectMembership.objects.create(
                    project=locked_project,
                    user=user,
                    role=role,
                    created_by=actor,
                    updated_by=actor,
                )
            except IntegrityError as exc:
                raise DomainError(
                    code="duplicate_membership",
                    detail="User already has an active project membership.",
                    status_code=HTTPStatus.CONFLICT,
                ) from exc
        else:
            membership.role = role
            membership.deleted_at = None
            membership.deleted_by = None
            membership.updated_by = actor
            membership.save(
                update_fields=["role", "deleted_at", "deleted_by", "updated_by", "updated_at"]
            )

        record_audit_log(
            actor=actor,
            action="membership.added",
            entity_type="project_membership",
            entity_id=membership.id,
            project=locked_project,
            after=membership_snapshot(membership),
        )
    return membership


def update_project_member(
    *,
    actor: Any,
    project: Project,
    membership: ProjectMembership,
    role: str,
) -> ProjectMembership:
    """Update a project membership role."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        locked_membership = locked_active_membership(
            project=locked_project,
            membership=membership,
        )
        if role == ProjectMembership.Role.OWNER:
            raise_invalid_role("Use ownership transfer to assign the owner role.")
        if locked_membership.role == ProjectMembership.Role.OWNER:
            raise DomainError(
                code="owner_required",
                detail="Owner membership cannot be changed without ownership transfer.",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        before = membership_snapshot(locked_membership)
        locked_membership.role = role
        locked_membership.updated_by = actor
        locked_membership.save(update_fields=["role", "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="membership.updated",
            entity_type="project_membership",
            entity_id=locked_membership.id,
            project=project,
            before=before,
            after=membership_snapshot(locked_membership),
        )
    return locked_membership


def remove_project_member(
    *,
    actor: Any,
    project: Project,
    membership: ProjectMembership,
) -> None:
    """Soft delete a project membership."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        locked_membership = locked_active_membership(
            project=locked_project,
            membership=membership,
        )
        if locked_membership.role == ProjectMembership.Role.OWNER:
            raise DomainError(
                code="owner_required",
                detail="Owner membership cannot be removed without ownership transfer.",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        before = membership_snapshot(locked_membership)
        now = timezone.now()
        locked_membership.deleted_at = now
        locked_membership.deleted_by = actor
        locked_membership.updated_by = actor
        locked_membership.save(
            update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"]
        )
        record_audit_log(
            actor=actor,
            action="membership.removed",
            entity_type="project_membership",
            entity_id=locked_membership.id,
            project=project,
            before=before,
            after=membership_snapshot(locked_membership),
        )


def transfer_project_ownership(*, actor: Any, project: Project, new_owner: Any) -> Project:
    """Transfer project ownership to another user."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        if locked_project.owner_id == new_owner.id:
            raise_conflict("Project is already owned by this user.")

        before = project_snapshot(locked_project)
        old_owner_membership = active_owner_membership(project=locked_project)
        new_owner_membership = (
            ProjectMembership.objects.select_for_update()
            .filter(
                project=locked_project,
                user=new_owner,
            )
            .order_by("-updated_at", "-id")
            .first()
        )

        old_owner_membership.role = ProjectMembership.Role.MANAGER
        old_owner_membership.updated_by = actor
        old_owner_membership.save(update_fields=["role", "updated_by", "updated_at"])

        if new_owner_membership is None:
            new_owner_membership = ProjectMembership.objects.create(
                project=locked_project,
                user=new_owner,
                role=ProjectMembership.Role.OWNER,
                created_by=actor,
                updated_by=actor,
            )
        else:
            new_owner_membership.role = ProjectMembership.Role.OWNER
            new_owner_membership.deleted_at = None
            new_owner_membership.deleted_by = None
            new_owner_membership.updated_by = actor
            new_owner_membership.save(
                update_fields=["role", "deleted_at", "deleted_by", "updated_by", "updated_at"]
            )

        locked_project.owner = new_owner
        locked_project.updated_by = actor
        locked_project.save(update_fields=["owner", "updated_by", "updated_at"])
        record_audit_log(
            actor=actor,
            action="project.ownership_transferred",
            entity_type="project",
            entity_id=locked_project.id,
            project=locked_project,
            before=before,
            after=project_snapshot(locked_project),
            metadata={
                "old_owner_id": actor.id,
                "new_owner_id": new_owner.id,
                "old_owner_membership_id": old_owner_membership.id,
                "new_owner_membership_id": new_owner_membership.id,
            },
        )
    return locked_project


def soft_delete_project(*, actor: Any, project: Project) -> None:
    """Soft delete a project and its active memberships."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_owner(actor=actor, project=locked_project)
        before = project_snapshot(locked_project)
        now = timezone.now()
        locked_project.deleted_at = now
        locked_project.deleted_by = actor
        locked_project.updated_by = actor
        locked_project.save(update_fields=["deleted_at", "deleted_by", "updated_by", "updated_at"])
        ProjectMembership.objects.filter(
            project=locked_project,
            deleted_at__isnull=True,
        ).update(
            deleted_at=now,
            deleted_by=actor,
            updated_by=actor,
            updated_at=now,
        )
        record_audit_log(
            actor=actor,
            action="project.deleted",
            entity_type="project",
            entity_id=locked_project.id,
            project=locked_project,
            before=before,
            after=project_snapshot(locked_project),
        )


def schedule_publish(*, actor: Any, project: Project, publish_at: datetime) -> Project:
    """Schedule a project publish time."""
    normalized_publish_at = validate_future_aware(value=publish_at)
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_SCHEDULE)
        ensure_close_after_publish(
            publish_at=normalized_publish_at,
            close_at=locked_project.close_at,
        )
        return update_schedule_field(
            actor=actor,
            project=locked_project,
            field="publish_at",
            value=normalized_publish_at,
            action="project.publish_scheduled",
        )


def cancel_publish_schedule(*, actor: Any, project: Project) -> Project:
    """Cancel a pending project publish schedule."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_SCHEDULE)
        return update_schedule_field(
            actor=actor,
            project=locked_project,
            field="publish_at",
            value=None,
            action="project.publish_schedule_cancelled",
        )


def schedule_close(*, actor: Any, project: Project, close_at: datetime) -> Project:
    """Schedule a project close time."""
    normalized_close_at = validate_future_aware(value=close_at)
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_SCHEDULE)
        ensure_close_after_publish(
            publish_at=locked_project.publish_at,
            close_at=normalized_close_at,
        )
        return update_schedule_field(
            actor=actor,
            project=locked_project,
            field="close_at",
            value=normalized_close_at,
            action="project.close_scheduled",
        )


def cancel_close_schedule(*, actor: Any, project: Project) -> Project:
    """Cancel a pending project close schedule."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_SCHEDULE)
        return update_schedule_field(
            actor=actor,
            project=locked_project,
            field="close_at",
            value=None,
            action="project.close_schedule_cancelled",
        )


def close_project(*, actor: Any, project: Project) -> Project:
    """Close an active project."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_CLOSE)
        if locked_project.state == Project.State.CLOSED:
            raise_conflict("Project is already closed.")
        before = project_snapshot(locked_project)
        locked_project.state = Project.State.CLOSED
        locked_project.closed_at = timezone.now()
        locked_project.close_at = None
        locked_project.updated_by = actor
        locked_project.save(
            update_fields=["state", "closed_at", "close_at", "updated_by", "updated_at"]
        )
        record_audit_log(
            actor=actor,
            action="project.closed",
            entity_type="project",
            entity_id=locked_project.id,
            project=locked_project,
            before=before,
            after=project_snapshot(locked_project),
        )
    return locked_project


def reopen_project(*, actor: Any, project: Project) -> Project:
    """Reopen a closed project."""
    with transaction.atomic():
        locked_project = lock_project(project=project)
        ensure_lifecycle(actor=actor, project=locked_project, action=policies.ACTION_REOPEN)
        if locked_project.state == Project.State.ACTIVE:
            raise_conflict("Project is already active.")
        before = project_snapshot(locked_project)
        locked_project.state = Project.State.ACTIVE
        locked_project.closed_at = None
        locked_project.close_at = None
        locked_project.updated_by = actor
        locked_project.save(
            update_fields=["state", "closed_at", "close_at", "updated_by", "updated_at"]
        )
        record_audit_log(
            actor=actor,
            action="project.reopened",
            entity_type="project",
            entity_id=locked_project.id,
            project=locked_project,
            before=before,
            after=project_snapshot(locked_project),
        )
    return locked_project


def update_schedule_field(
    *,
    actor: Any,
    project: Project,
    field: str,
    value: datetime | None,
    action: str,
) -> Project:
    """Update one schedule field and write an audit log."""
    before = project_snapshot(project)
    setattr(project, field, value)
    project.updated_by = actor
    project.save(update_fields=[field, "updated_by", "updated_at"])
    record_audit_log(
        actor=actor,
        action=action,
        entity_type="project",
        entity_id=project.id,
        project=project,
        before=before,
        after=project_snapshot(project),
    )
    return project


def lock_project(*, project: Project) -> Project:
    """Lock and return the current project row."""
    return Project.objects.select_for_update().get(pk=project.pk)


def locked_active_membership(
    *,
    project: Project,
    membership: ProjectMembership,
) -> ProjectMembership:
    """Lock and return an active project membership."""
    locked_membership = (
        ProjectMembership.objects.select_for_update()
        .filter(project=project, pk=membership.pk, deleted_at__isnull=True)
        .first()
    )
    if locked_membership is None:
        selectors.raise_not_found()
    return locked_membership


def ensure_owner(*, actor: Any, project: Project) -> None:
    """Raise a permission error unless actor owns the project."""
    membership = selectors.membership_for_user(project=project, user=actor)
    if not policies.can_manage_members(actor=actor, project=project, membership=membership):
        raise_permission_denied()


def ensure_lifecycle(*, actor: Any, project: Project, action: str) -> None:
    """Raise a permission error unless actor can perform a lifecycle action."""
    membership = selectors.membership_for_user(project=project, user=actor)
    allowed = {
        policies.ACTION_SCHEDULE: policies.can_schedule_project,
        policies.ACTION_CLOSE: policies.can_close_project,
        policies.ACTION_REOPEN: policies.can_reopen_project,
    }[action](actor=actor, project=project, membership=membership)
    if not allowed:
        raise_permission_denied()


def active_owner_membership(*, project: Project) -> ProjectMembership:
    """Return the active owner membership or raise a conflict error."""
    membership = (
        ProjectMembership.objects.select_for_update()
        .filter(
            project=project,
            role=ProjectMembership.Role.OWNER,
            deleted_at__isnull=True,
        )
        .first()
    )
    if membership is None or membership.user_id != project.owner_id:
        raise_conflict("Project owner membership is inconsistent.")
    return membership


def soft_deleted_membership(*, project: Project, user: Any) -> ProjectMembership | None:
    """Return the latest soft-deleted membership for a user."""
    return (
        ProjectMembership.objects.select_for_update()
        .filter(project=project, user=user, deleted_at__isnull=False)
        .order_by("-updated_at", "-id")
        .first()
    )


def validate_future_aware(*, value: datetime) -> datetime:
    """Validate and normalize a future aware datetime."""
    if timezone.is_naive(value):
        raise_invalid_schedule("Timestamp must include timezone information.")
    normalized = value.astimezone(UTC)
    if normalized <= timezone.now():
        raise_invalid_schedule("Timestamp must be in the future.")
    return normalized


def ensure_close_after_publish(
    *,
    publish_at: datetime | None,
    close_at: datetime | None,
) -> None:
    """Validate that close schedule is after publish schedule."""
    if publish_at and close_at and close_at <= publish_at:
        raise_invalid_schedule("Close schedule must be after publish schedule.")


def project_snapshot(project: Project) -> dict:
    """Return a JSON-safe project snapshot."""
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
        "visibility": project.visibility,
        "state": project.state,
        "public_comment_policy": project.public_comment_policy,
        "publish_at": datetime_value(project.publish_at),
        "published_at": datetime_value(project.published_at),
        "close_at": datetime_value(project.close_at),
        "closed_at": datetime_value(project.closed_at),
        "deleted_at": datetime_value(project.deleted_at),
    }


def membership_snapshot(membership: ProjectMembership) -> dict:
    """Return a JSON-safe membership snapshot."""
    return {
        "id": membership.id,
        "project_id": membership.project_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "deleted_at": datetime_value(membership.deleted_at),
    }


def datetime_value(value: datetime | None) -> str | None:
    """Return an ISO formatted datetime or none."""
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def raise_permission_denied() -> None:
    """Raise the standard permission-denied error."""
    raise DomainError(
        code="permission_denied",
        detail="You do not have permission to perform this action.",
        status_code=HTTPStatus.FORBIDDEN,
    )


def raise_invalid_role(detail: str) -> None:
    """Raise an invalid role error."""
    raise DomainError(
        code="invalid_role",
        detail=detail,
        field="role",
        status_code=HTTPStatus.BAD_REQUEST,
    )


def raise_invalid_schedule(detail: str) -> None:
    """Raise an invalid schedule error."""
    raise DomainError(
        code="invalid_schedule",
        detail=detail,
        status_code=HTTPStatus.BAD_REQUEST,
    )


def raise_conflict(detail: str) -> None:
    """Raise a state conflict error."""
    raise DomainError(
        code="conflict",
        detail=detail,
        status_code=HTTPStatus.CONFLICT,
    )
