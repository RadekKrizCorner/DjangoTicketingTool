"""Integration permission matrices for attachment endpoints."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.models import Project, ProjectMembership
from apps.projects.services import close_project
from tests.factories import (
    add_project_member,
    auth_header,
    create_comment,
    create_project,
    create_task,
    create_user,
)

ATTACHMENT_PARENTS = ("task", "comment")
ATTACHMENT_ACTOR_KINDS = ("owner", "manager", "member", "viewer", "outsider")
PROJECT_STATES = (Project.State.ACTIVE, Project.State.CLOSED)


def attachment_expected_status(*, parent_kind: str, actor_kind: str, project_state: str) -> int:
    """Return the expected attachment upload status for a matrix case."""
    if parent_kind == "comment":
        return 201
    if project_state == Project.State.CLOSED:
        return 409
    if actor_kind in {"owner", "manager", "member"}:
        return 201
    return 403


def attachment_error_code(*, expected_status: int) -> str | None:
    """Return the expected attachment error code for a matrix status."""
    if expected_status == 403:
        return "permission_denied"
    if expected_status == 409:
        return "project_closed"
    return None


def attachment_permission_cases() -> list[dict]:
    """Return all attachment parent, role, and project-state cases."""
    cases = []
    for parent_kind in ATTACHMENT_PARENTS:
        for actor_kind in ATTACHMENT_ACTOR_KINDS:
            for project_state in PROJECT_STATES:
                expected_status = attachment_expected_status(
                    parent_kind=parent_kind,
                    actor_kind=actor_kind,
                    project_state=project_state,
                )
                cases.append(
                    {
                        "parent_kind": parent_kind,
                        "actor_kind": actor_kind,
                        "project_state": project_state,
                        "expected_status": expected_status,
                        "error_code": attachment_error_code(expected_status=expected_status),
                    }
                )
    return cases


def attachment_actor(*, actor_kind: str, owner, project: Project):
    """Return the actor for one attachment matrix case."""
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


def upload_path(*, parent_kind: str, project_id: int, task_id: int, comment_id: int) -> str:
    """Return an attachment upload path for a task or comment parent."""
    if parent_kind == "task":
        return f"/api/v1/projects/{project_id}/tasks/{task_id}/attachments/"
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/attachments/"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(*attachment_permission_cases())
def test_attachment_parent_role_state_upload_matrix(
    client,
    parent_kind,
    actor_kind,
    project_state,
    expected_status,
    error_code,
):
    """Verify attachment upload permissions for every parent, role, and project state."""
    owner = create_user()
    assignee = create_user()
    project = create_project(
        owner=owner,
        name=f"Attachment {parent_kind} {actor_kind} {project_state}",
        visibility=Project.Visibility.PUBLIC,
        public_comment_policy=Project.PublicCommentPolicy.AUTHENTICATED_USERS,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)
    comment = create_comment(actor=owner, task=task, body="Upload parent")
    actor = attachment_actor(actor_kind=actor_kind, owner=owner, project=project)
    if project_state == Project.State.CLOSED:
        close_project(actor=owner, project=project)
    file_obj = SimpleUploadedFile("matrix.log", b"log line", content_type="text/plain")

    response = client.post(
        upload_path(
            parent_kind=parent_kind,
            project_id=project.id,
            task_id=task.id,
            comment_id=comment.id,
        ),
        {"file": file_obj},
        **auth_header(actor),
    )

    assert response.status_code == expected_status
    if error_code:
        assert response.json()["errors"][0]["code"] == error_code
