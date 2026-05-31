"""Integration permission matrices for project endpoints."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.projects.models import Project, ProjectMembership
from apps.projects.services import close_project
from tests.factories import (
    add_project_member,
    auth_header,
    create_project,
    create_user,
    json_patch,
    json_post,
    json_put,
)

PROJECT_ACTIONS = (
    "read",
    "update",
    "delete",
    "schedule_publish",
    "close",
    "reopen",
    "audit",
    "add_member",
)
PROJECT_ACTOR_KINDS = ("owner", "manager", "member", "viewer", "staff", "outsider")


def project_expected_status(*, actor_kind: str, action: str) -> int:
    """Return the expected project permission status for a matrix case."""
    if action == "read":
        return 200
    if actor_kind == "owner":
        return 204 if action == "delete" else 200 if action != "add_member" else 201
    if actor_kind == "staff" and action in {"schedule_publish", "close", "reopen"}:
        return 200
    return 403


def project_permission_cases() -> list[dict]:
    """Return all project role and action permission cases."""
    cases = []
    for actor_kind in PROJECT_ACTOR_KINDS:
        for action in PROJECT_ACTIONS:
            cases.append(
                {
                    "actor_kind": actor_kind,
                    "action": action,
                    "expected_status": project_expected_status(
                        actor_kind=actor_kind,
                        action=action,
                    ),
                }
            )
    return cases


def project_actor(*, actor_kind: str, owner, project: Project):
    """Return the actor for one project matrix case."""
    if actor_kind == "owner":
        return owner
    if actor_kind == "staff":
        return create_user(is_staff=True)
    actor = create_user()
    if actor_kind != "outsider":
        add_project_member(
            actor=owner,
            project=project,
            user=actor,
            role=getattr(ProjectMembership.Role, actor_kind.upper()),
        )
    return actor


def execute_project_action(*, client, action: str, actor, owner, project: Project):
    """Execute one project action through the API."""
    base_path = f"/api/v1/projects/{project.id}/"
    if action == "read":
        return client.get(base_path, **auth_header(actor))
    if action == "update":
        return json_patch(client, base_path, {"name": "Updated project"}, actor)
    if action == "delete":
        return client.delete(base_path, **auth_header(actor))
    if action == "schedule_publish":
        publish_at = (timezone.now() + timedelta(days=1)).isoformat()
        return json_put(client, f"{base_path}publish-schedule/", {"publish_at": publish_at}, actor)
    if action == "close":
        return json_post(client, f"{base_path}close/", {}, actor)
    if action == "reopen":
        close_project(actor=owner, project=project)
        return json_post(client, f"{base_path}reopen/", {}, actor)
    if action == "audit":
        return client.get(f"{base_path}audit-log/", **auth_header(actor))
    target = create_user()
    return json_post(
        client,
        f"{base_path}members/",
        {"user_id": target.id, "role": ProjectMembership.Role.MEMBER},
        actor,
    )


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(*project_permission_cases())
def test_project_role_action_permission_matrix(client, actor_kind, action, expected_status):
    """Verify project endpoint permissions for every supported role and action."""
    owner = create_user()
    project = create_project(
        owner=owner,
        name=f"Project {actor_kind} {action}",
        visibility=Project.Visibility.PUBLIC,
    )
    actor = project_actor(actor_kind=actor_kind, owner=owner, project=project)

    response = execute_project_action(
        client=client,
        action=action,
        actor=actor,
        owner=owner,
        project=project,
    )

    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json()["errors"][0]["code"] == "permission_denied"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(
        path="/api/v1/projects/",
        authenticated=False,
        expected_status=401,
        error_code="authentication_required",
    ),
    dict(
        path="/api/v1/projects/{public_id}/",
        authenticated=False,
        expected_status=401,
        error_code="authentication_required",
    ),
    dict(
        path="/api/v1/projects/{private_id}/",
        authenticated=False,
        expected_status=401,
        error_code="authentication_required",
    ),
    dict(
        path="/api/v1/projects/{public_id}/",
        authenticated=True,
        expected_status=200,
        error_code=None,
    ),
    dict(
        path="/api/v1/projects/{private_id}/",
        authenticated=True,
        expected_status=404,
        error_code="not_found",
    ),
    dict(
        path="/api/v1/health/live/",
        authenticated=False,
        expected_status=200,
        error_code=None,
    ),
    dict(path="/api/v1/schema/", authenticated=False, expected_status=200, error_code=None),
)
def test_visibility_authentication_matrix(
    client,
    path,
    authenticated,
    expected_status,
    error_code,
):
    """Verify anonymous users see only public non-domain endpoints."""
    owner = create_user()
    outsider = create_user()
    public_project = create_project(
        owner=owner,
        name="Visible API Project",
        visibility=Project.Visibility.PUBLIC,
    )
    private_project = create_project(
        owner=owner,
        name="Hidden API Project",
        visibility=Project.Visibility.PRIVATE,
    )
    resolved_path = path.format(public_id=public_project.id, private_id=private_project.id)
    headers = auth_header(outsider) if authenticated else {}

    response = client.get(resolved_path, **headers)

    assert response.status_code == expected_status
    if error_code:
        assert response.json()["errors"][0]["code"] == error_code
