"""Integration permission matrices for task endpoints."""

import pytest

from apps.projects.models import Project, ProjectMembership
from apps.projects.services import close_project
from apps.tasks.models import Task
from tests.factories import (
    add_project_member,
    auth_header,
    create_project,
    create_task,
    create_user,
    json_patch,
    json_post,
)

TASK_ACTIONS = ("read", "create", "update", "delete", "transition")
TASK_ACTOR_KINDS = ("owner", "manager", "member", "viewer", "outsider")
PROJECT_STATES = (Project.State.ACTIVE, Project.State.CLOSED)


def task_expected_status(*, actor_kind: str, action: str, project_state: str) -> int:
    """Return the expected task permission status for a matrix case."""
    if action == "read":
        return 200
    if project_state == Project.State.CLOSED:
        return 409
    if actor_kind in {"owner", "manager", "member"}:
        return 201 if action == "create" else 204 if action == "delete" else 200
    return 403


def task_error_code(*, expected_status: int) -> str | None:
    """Return the expected error code for a task matrix status."""
    if expected_status == 403:
        return "permission_denied"
    if expected_status == 409:
        return "project_closed"
    return None


def task_permission_cases() -> list[dict]:
    """Return all task role, action, and project-state permission cases."""
    cases = []
    for actor_kind in TASK_ACTOR_KINDS:
        for action in TASK_ACTIONS:
            for project_state in PROJECT_STATES:
                expected_status = task_expected_status(
                    actor_kind=actor_kind,
                    action=action,
                    project_state=project_state,
                )
                cases.append(
                    {
                        "actor_kind": actor_kind,
                        "action": action,
                        "project_state": project_state,
                        "expected_status": expected_status,
                        "error_code": task_error_code(expected_status=expected_status),
                    }
                )
    return cases


def task_url(project_id: int, task_id: int | None = None, suffix: str = "") -> str:
    """Return a project task URL."""
    if task_id is None:
        return f"/api/v1/projects/{project_id}/tasks/{suffix}"
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/{suffix}"


def task_actor(*, actor_kind: str, owner, project: Project):
    """Return the actor for one task matrix case."""
    if actor_kind == "owner":
        return owner
    actor = create_user()
    if actor_kind != "outsider":
        add_project_member(
            actor=owner,
            project=project,
            user=actor,
            role=getattr(ProjectMembership.Role, actor_kind.upper()),
        )
    return actor


def execute_task_action(*, client, action: str, actor, project: Project, task: Task):
    """Execute one task action through the API."""
    if action == "read":
        return client.get(task_url(project.id, task.id), **auth_header(actor))
    if action == "create":
        return json_post(
            client,
            task_url(project.id),
            {"title": "Created by matrix", "assignee_id": task.assignee_id},
            actor,
        )
    if action == "update":
        return json_patch(client, task_url(project.id, task.id), {"title": "Updated"}, actor)
    if action == "delete":
        return client.delete(task_url(project.id, task.id), **auth_header(actor))
    return json_post(
        client,
        task_url(project.id, task.id, "transition/"),
        {"status": Task.Status.ACCEPTED},
        actor,
    )


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(*task_permission_cases())
def test_task_role_action_state_permission_matrix(
    client,
    actor_kind,
    action,
    project_state,
    expected_status,
    error_code,
):
    """Verify task permissions for every role, action, and project state."""
    owner = create_user()
    assignee = create_user()
    project = create_project(
        owner=owner,
        name=f"Task {actor_kind} {action} {project_state}",
        visibility=Project.Visibility.PUBLIC,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)
    actor = task_actor(actor_kind=actor_kind, owner=owner, project=project)
    if project_state == Project.State.CLOSED:
        close_project(actor=owner, project=project)

    response = execute_task_action(
        client=client,
        action=action,
        actor=actor,
        project=project,
        task=task,
    )

    assert response.status_code == expected_status
    if error_code:
        assert response.json()["errors"][0]["code"] == error_code
