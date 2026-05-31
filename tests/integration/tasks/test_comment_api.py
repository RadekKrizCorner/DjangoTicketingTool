"""Integration tests for task comment API endpoints."""

import pytest

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
    json_post,
)
from tests.integration.tasks.test_task_api import create_task


def comments_url(project_id, task_id):
    """Return the task comments URL."""
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(visibility="private", policy="members_only", actor_kind="member", expected_status=201),
    dict(visibility="private", policy="members_only", actor_kind="outsider", expected_status=404),
    dict(visibility="public", policy="members_only", actor_kind="outsider", expected_status=403),
    dict(
        visibility="public",
        policy="authenticated_users",
        actor_kind="outsider",
        expected_status=201,
    ),
)
def test_comment_create_access_matrix(client, visibility, policy, actor_kind, expected_status):
    """Verify task comments follow project visibility and comment policy."""
    owner = create_user(f"comment-owner-{visibility}-{actor_kind}@example.com")
    member = create_user(f"comment-member-{visibility}-{actor_kind}@example.com")
    outsider = create_user(f"comment-outsider-{visibility}-{actor_kind}@example.com")
    project = create_project(client, owner, name=f"Comments {visibility}", visibility=visibility)
    patch_response = client.patch(
        f"/api/v1/projects/{project['id']}/",
        data={"public_comment_policy": policy},
        content_type="application/json",
        **auth_header(owner),
    )
    add_member(client, owner, project["id"], member, role="viewer")
    task = create_task(client, owner, project["id"], member)
    actor = member if actor_kind == "member" else outsider

    response = json_post(
        client,
        comments_url(project["id"], task["id"]),
        {"body": "Looks good"},
        actor,
    )

    assert patch_response.status_code == 200
    assert response.status_code == expected_status
    if expected_status >= 400:
        assert response.json()["errors"][0]["code"] in {"not_found", "permission_denied"}
