"""Integration permission matrices for task comments."""

import pytest

from apps.projects.models import Project, ProjectMembership
from tests.factories import (
    add_project_member,
    auth_header,
    create_comment,
    create_project,
    create_task,
    create_user,
    json_patch,
)

COMMENT_ACTIONS = ("update", "delete")
COMMENT_ACTOR_KINDS = ("owner", "manager", "member", "viewer", "outsider")
AUTHOR_RELATIONS = ("author", "non_author")


def comment_expected_status(*, actor_kind: str, action: str, author_relation: str) -> int:
    """Return the expected comment permission status for a matrix case."""
    if author_relation == "author":
        return 204 if action == "delete" else 200
    if action == "delete" and actor_kind in {"owner", "manager"}:
        return 204
    return 403


def comment_permission_cases() -> list[dict]:
    """Return all comment role, action, and author-relation cases."""
    cases = []
    for actor_kind in COMMENT_ACTOR_KINDS:
        for action in COMMENT_ACTIONS:
            for author_relation in AUTHOR_RELATIONS:
                expected_status = comment_expected_status(
                    actor_kind=actor_kind,
                    action=action,
                    author_relation=author_relation,
                )
                cases.append(
                    {
                        "actor_kind": actor_kind,
                        "action": action,
                        "author_relation": author_relation,
                        "expected_status": expected_status,
                    }
                )
    return cases


def comment_url(project_id: int, task_id: int, comment_id: int) -> str:
    """Return a task comment detail URL."""
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/"


def comment_actor(*, actor_kind: str, owner, project: Project):
    """Return the actor for one comment matrix case."""
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


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(*comment_permission_cases())
def test_comment_action_author_permission_matrix(
    client,
    actor_kind,
    action,
    author_relation,
    expected_status,
):
    """Verify comment update and delete permissions for every actor relation."""
    owner = create_user()
    assignee = create_user()
    fallback_author = create_user()
    project = create_project(
        owner=owner,
        name=f"Comment {actor_kind} {action} {author_relation}",
        visibility=Project.Visibility.PUBLIC,
        public_comment_policy=Project.PublicCommentPolicy.AUTHENTICATED_USERS,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=fallback_author,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)
    actor = comment_actor(actor_kind=actor_kind, owner=owner, project=project)
    author = actor if author_relation == "author" else fallback_author
    comment = create_comment(actor=author, task=task, body="Matrix comment")

    if action == "update":
        response = json_patch(
            client,
            comment_url(project.id, task.id, comment.id),
            {"body": "Edited comment"},
            actor,
        )
    else:
        response = client.delete(comment_url(project.id, task.id, comment.id), **auth_header(actor))

    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json()["errors"][0]["code"] == "permission_denied"
