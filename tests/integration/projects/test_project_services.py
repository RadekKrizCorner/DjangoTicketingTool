"""Integration tests for project domain services."""

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.common.errors import DomainError
from apps.projects import services
from apps.projects.models import Project, ProjectMembership


def create_user(email):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email=email,
        password="StrongerPass123!",
        display_name=email.split("@")[0].title(),
    )


def create_service_project(owner, *, visibility=Project.Visibility.PRIVATE):
    """Create a project through the service layer."""
    return services.create_project(
        actor=owner,
        data={
            "name": "Service Project",
            "description": "Service test project",
            "visibility": visibility,
        },
    )


def assert_domain_error(error_info, *, code, status_code):
    """Assert a domain error code and status."""
    error = error_info.value
    assert error.code == code
    assert error.status_code == status_code


def future_datetime(days):
    """Return an aware future datetime."""
    return timezone.now() + timedelta(days=days)


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(operation="update_project"),
    dict(operation="add_member"),
    dict(operation="update_member"),
    dict(operation="remove_member"),
    dict(operation="transfer_ownership"),
    dict(operation="soft_delete_project"),
    dict(operation="schedule_publish"),
    dict(operation="cancel_publish_schedule"),
    dict(operation="schedule_close"),
    dict(operation="cancel_close_schedule"),
    dict(operation="close_project"),
    dict(operation="reopen_project"),
)
def test_stale_owner_state_cannot_mutate_after_owner_changes_in_database(operation):
    """Verify services re-check permissions after locking the current project row."""
    old_owner = create_user(f"old-owner-{operation}@example.com")
    current_owner = create_user(f"current-owner-{operation}@example.com")
    member = create_user(f"member-{operation}@example.com")
    target = create_user(f"target-{operation}@example.com")
    stale_project = create_service_project(old_owner)
    membership = services.add_project_member(
        actor=old_owner,
        project=stale_project,
        user=member,
        role=ProjectMembership.Role.VIEWER,
    )
    Project.objects.filter(pk=stale_project.pk).update(owner=current_owner)
    prepare_stale_permission_operation(operation, stale_project)

    with pytest.raises(DomainError) as error_info:
        execute_stale_permission_operation(
            operation,
            actor=old_owner,
            project=stale_project,
            membership=membership,
            target=target,
        )

    assert_domain_error(
        error_info,
        code="permission_denied",
        status_code=HTTPStatus.FORBIDDEN,
    )


def prepare_stale_permission_operation(operation, project):
    """Prepare current database state for one stale permission operation."""
    if operation == "cancel_publish_schedule":
        Project.objects.filter(pk=project.pk).update(publish_at=future_datetime(2))
    if operation == "cancel_close_schedule":
        Project.objects.filter(pk=project.pk).update(close_at=future_datetime(2))
    if operation == "reopen_project":
        Project.objects.filter(pk=project.pk).update(
            state=Project.State.CLOSED,
            closed_at=timezone.now(),
        )


def execute_stale_permission_operation(operation, *, actor, project, membership, target):
    """Execute one service operation with stale project ownership state."""
    if operation == "update_project":
        return services.update_project(actor=actor, project=project, data={"name": "Race"})
    if operation == "add_member":
        return services.add_project_member(
            actor=actor,
            project=project,
            user=target,
            role=ProjectMembership.Role.VIEWER,
        )
    if operation == "update_member":
        return services.update_project_member(
            actor=actor,
            project=project,
            membership=membership,
            role=ProjectMembership.Role.MANAGER,
        )
    if operation == "remove_member":
        return services.remove_project_member(actor=actor, project=project, membership=membership)
    if operation == "transfer_ownership":
        return services.transfer_project_ownership(actor=actor, project=project, new_owner=target)
    if operation == "soft_delete_project":
        return services.soft_delete_project(actor=actor, project=project)
    if operation == "schedule_publish":
        return services.schedule_publish(
            actor=actor,
            project=project,
            publish_at=future_datetime(2),
        )
    if operation == "cancel_publish_schedule":
        return services.cancel_publish_schedule(actor=actor, project=project)
    if operation == "schedule_close":
        return services.schedule_close(actor=actor, project=project, close_at=future_datetime(2))
    if operation == "cancel_close_schedule":
        return services.cancel_close_schedule(actor=actor, project=project)
    if operation == "close_project":
        return services.close_project(actor=actor, project=project)
    if operation == "reopen_project":
        return services.reopen_project(actor=actor, project=project)
    raise AssertionError(f"Unsupported operation: {operation}")


@pytest.mark.integration
@pytest.mark.django_db
def test_schedule_publish_validates_against_locked_current_close_schedule():
    """Verify publish scheduling checks the locked current close schedule."""
    owner = create_user("owner-schedule-publish-race@example.com")
    project = create_service_project(owner)
    Project.objects.filter(pk=project.pk).update(close_at=future_datetime(1))

    with pytest.raises(DomainError) as error_info:
        services.schedule_publish(actor=owner, project=project, publish_at=future_datetime(2))

    assert_domain_error(
        error_info,
        code="invalid_schedule",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    project.refresh_from_db()
    assert project.publish_at is None


@pytest.mark.integration
@pytest.mark.django_db
def test_schedule_close_validates_against_locked_current_publish_schedule():
    """Verify close scheduling checks the locked current publish schedule."""
    owner = create_user("owner-schedule-close-race@example.com")
    project = create_service_project(owner)
    Project.objects.filter(pk=project.pk).update(publish_at=future_datetime(2))

    with pytest.raises(DomainError) as error_info:
        services.schedule_close(actor=owner, project=project, close_at=future_datetime(1))

    assert_domain_error(
        error_info,
        code="invalid_schedule",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    project.refresh_from_db()
    assert project.close_at is None


@pytest.mark.integration
@pytest.mark.django_db
def test_project_validation_rejects_owner_without_matching_owner_membership():
    """Verify project validation enforces owner membership consistency."""
    owner = create_user("owner-project-clean@example.com")
    other_user = create_user("other-project-clean@example.com")
    project = create_service_project(owner)
    project.owner = other_user

    with pytest.raises(DjangoValidationError) as error_info:
        project.full_clean()

    assert "owner" in error_info.value.message_dict


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_membership_validation_rejects_user_change():
    """Verify owner membership validation protects the owner user."""
    owner = create_user("owner-membership-user-clean@example.com")
    other_user = create_user("other-membership-user-clean@example.com")
    project = create_service_project(owner)
    membership = ProjectMembership.objects.get(project=project, user=owner)
    membership.user = other_user

    with pytest.raises(DjangoValidationError) as error_info:
        membership.full_clean()

    assert "user" in error_info.value.message_dict


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_membership_validation_rejects_role_change():
    """Verify owner membership validation protects the owner role."""
    owner = create_user("owner-membership-role-clean@example.com")
    project = create_service_project(owner)
    membership = ProjectMembership.objects.get(project=project, user=owner)
    membership.role = ProjectMembership.Role.MANAGER

    with pytest.raises(DjangoValidationError) as error_info:
        membership.full_clean()

    assert "role" in error_info.value.message_dict
