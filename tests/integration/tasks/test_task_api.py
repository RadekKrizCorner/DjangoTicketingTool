"""Integration tests for task API endpoints."""

import pytest

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
    json_post,
)


def task_url(project_id, task_id=None, suffix=""):
    """Return a project task URL."""
    if task_id is None:
        return f"/api/v1/projects/{project_id}/tasks/{suffix}"
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/{suffix}"


def create_task(client, owner, project_id, assignee, title="Task"):
    """Create a task through the API."""
    response = json_post(
        client,
        task_url(project_id),
        {"title": title, "description": "Task body", "assignee_id": assignee.id},
        owner,
    )
    assert response.status_code == 201
    return response.json()["data"]


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(role="owner", expected_status=201),
    dict(role="manager", expected_status=201),
    dict(role="member", expected_status=201),
    dict(role="viewer", expected_status=403),
    dict(role="outsider", expected_status=403),
)
def test_task_create_permission_matrix(client, role, expected_status):
    """Verify only writable project roles can create tasks."""
    owner = create_user(f"task-owner-{role}@example.com")
    actor = owner if role == "owner" else create_user(f"task-actor-{role}@example.com")
    assignee = create_user(f"task-assignee-{role}@example.com")
    project = create_project(client, owner, name=f"Task {role}", visibility="public")
    add_member(client, owner, project["id"], assignee, role="member")
    if role not in {"owner", "outsider"}:
        add_member(client, owner, project["id"], actor, role=role)

    response = json_post(
        client,
        task_url(project["id"]),
        {"title": "API task", "assignee_id": assignee.id},
        actor,
    )

    assert response.status_code == expected_status
    if expected_status >= 400:
        assert response.json()["errors"][0]["code"] == "permission_denied"


@pytest.mark.integration
@pytest.mark.django_db
def test_task_transition_rejects_invalid_workflow_step(client):
    """Verify task status transitions must follow the workflow matrix."""
    owner = create_user("task-owner-transition@example.com")
    assignee = create_user("task-assignee-transition@example.com")
    project = create_project(client, owner, name="Transition", visibility="private")
    add_member(client, owner, project["id"], assignee, role="member")
    task = create_task(client, owner, project["id"], assignee)

    response = json_post(
        client,
        task_url(project["id"], task["id"], "transition/"),
        {"status": "completed"},
        owner,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "invalid_transition"


@pytest.mark.integration
@pytest.mark.django_db
def test_closed_project_rejects_task_mutations(client):
    """Verify closed projects reject task creation and updates."""
    owner = create_user("task-owner-closed@example.com")
    assignee = create_user("task-assignee-closed@example.com")
    project = create_project(client, owner, name="Closed Tasks", visibility="private")
    add_member(client, owner, project["id"], assignee, role="member")
    task = create_task(client, owner, project["id"], assignee)
    close_response = json_post(client, f"/api/v1/projects/{project['id']}/close/", {}, owner)

    create_response = json_post(
        client,
        task_url(project["id"]),
        {"title": "Blocked", "assignee_id": assignee.id},
        owner,
    )
    patch_response = client.patch(
        task_url(project["id"], task["id"]),
        data={"title": "Blocked edit"},
        content_type="application/json",
        **auth_header(owner),
    )

    assert close_response.status_code == 200
    assert create_response.status_code == 409
    assert create_response.json()["errors"][0]["code"] == "project_closed"
    assert patch_response.status_code == 409
    assert patch_response.json()["errors"][0]["code"] == "project_closed"
