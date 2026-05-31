"""Test data factories."""

from itertools import count

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task

DEFAULT_PASSWORD = "StrongerPass123!"
_SEQUENCE = count(1)


def unique_email(prefix: str = "user") -> str:
    """Return a unique test email address."""
    return f"{prefix}-{next(_SEQUENCE)}@example.com"


def create_user(
    *,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    display_name: str | None = None,
    is_staff: bool = False,
    **kwargs,
):
    """Create a test user."""
    user_model = get_user_model()
    normalized_email = email or unique_email()
    return user_model.objects.create_user(
        email=normalized_email,
        password=password,
        display_name=display_name or normalized_email.split("@")[0].title(),
        is_staff=is_staff,
        **kwargs,
    )


def auth_header(user) -> dict[str, str]:
    """Return a JWT authorization header for a user."""
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def json_post(client, path: str, payload: dict, user):
    """POST JSON as an authenticated user."""
    return client.post(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def json_put(client, path: str, payload: dict, user):
    """PUT JSON as an authenticated user."""
    return client.put(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def json_patch(client, path: str, payload: dict, user):
    """PATCH JSON as an authenticated user."""
    return client.patch(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def create_project(
    *,
    owner,
    name: str = "Project",
    visibility: str = Project.Visibility.PRIVATE,
    **kwargs,
) -> Project:
    """Create a project through the project service."""
    from apps.projects.services import create_project as service_create_project

    data = {
        "name": name,
        "description": kwargs.pop("description", ""),
        "visibility": visibility,
        **kwargs,
    }
    return service_create_project(actor=owner, data=data)


def add_project_member(
    *,
    actor,
    project: Project,
    user,
    role: str = ProjectMembership.Role.MEMBER,
) -> ProjectMembership:
    """Add a project member through the project service."""
    from apps.projects.services import add_project_member as service_add_project_member

    return service_add_project_member(actor=actor, project=project, user=user, role=role)


def create_task(
    *,
    actor,
    project: Project,
    assignee,
    title: str = "Task",
    **kwargs,
) -> Task:
    """Create a task through the task service."""
    from apps.tasks.services import create_task as service_create_task

    data = {
        "title": title,
        "description": kwargs.pop("description", ""),
        "assignee": assignee,
        **kwargs,
    }
    return service_create_task(actor=actor, project=project, data=data)


def create_comment(*, actor, task: Task, body: str = "Comment"):
    """Create a task comment through the task service."""
    from apps.tasks.services import create_comment as service_create_comment

    return service_create_comment(actor=actor, task=task, body=body)
