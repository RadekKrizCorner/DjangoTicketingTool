"""Integration tests for UI-facing API contract fields."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.projects.models import Project
from apps.tasks.models import Task
from tests.factories import (
    add_project_member,
    auth_header,
    create_comment,
    create_project,
    create_task,
    create_user,
    json_post,
)


def user_summary(user) -> dict:
    """Return the expected public user summary shape."""
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_current_user_includes_staff_flag(client):
    """Verify current-user output includes staff capability source data."""
    staff_user = create_user(email="ui-staff@example.com", is_staff=True)

    response = client.get("/api/v1/users/me/", **auth_header(staff_user))

    assert response.status_code == 200
    assert response.json()["data"] == {
        **user_summary(staff_user),
        "is_staff": True,
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_project_outputs_include_user_summaries_membership_and_capabilities(client):
    """Verify project and membership responses expose UI contract fields."""
    owner = create_user(email="ui-owner@example.com")
    member = create_user(email="ui-member@example.com")
    outsider = create_user(email="ui-outsider@example.com")
    staff_user = create_user(email="ui-staff-lifecycle@example.com", is_staff=True)
    project = create_project(owner=owner, name="UI Project", visibility=Project.Visibility.PUBLIC)
    membership = add_project_member(actor=owner, project=project, user=member, role="manager")

    owner_response = client.get(f"/api/v1/projects/{project.id}/", **auth_header(owner))
    outsider_response = client.get(f"/api/v1/projects/{project.id}/", **auth_header(outsider))
    staff_response = client.get(f"/api/v1/projects/{project.id}/", **auth_header(staff_user))
    members_response = client.get(f"/api/v1/projects/{project.id}/members/", **auth_header(owner))

    owner_data = owner_response.json()["data"]
    outsider_data = outsider_response.json()["data"]
    staff_data = staff_response.json()["data"]
    member_data = next(
        item for item in members_response.json()["data"] if item["id"] == membership.id
    )

    assert owner_response.status_code == 200
    assert owner_data["owner"] == user_summary(owner)
    assert owner_data["my_membership"]["role"] == "owner"
    assert owner_data["capabilities"] == {
        "can_update": True,
        "can_delete": True,
        "can_manage_members": True,
        "can_transfer_ownership": True,
        "can_schedule": True,
        "can_close": True,
        "can_reopen": False,
        "can_read_audit_log": True,
        "can_create_task": True,
        "can_comment": True,
        "can_upload_task_attachment": True,
        "can_upload_comment_attachment": True,
    }
    assert outsider_response.status_code == 200
    assert outsider_data["my_membership"] is None
    assert outsider_data["capabilities"]["can_update"] is False
    assert outsider_data["capabilities"]["can_comment"] is False
    assert staff_response.status_code == 200
    assert staff_data["capabilities"]["can_schedule"] is True
    assert staff_data["capabilities"]["can_close"] is True
    assert members_response.status_code == 200
    assert member_data["user"] == user_summary(member)


@pytest.mark.integration
@pytest.mark.django_db
def test_project_capabilities_role_matrix(client):
    """Verify project capabilities reflect owner, roles, staff, and public comment policy."""
    owner = create_user(email="ui-matrix-owner@example.com")
    manager = create_user(email="ui-matrix-manager@example.com")
    member = create_user(email="ui-matrix-member@example.com")
    viewer = create_user(email="ui-matrix-viewer@example.com")
    outsider = create_user(email="ui-matrix-outsider@example.com")
    staff_user = create_user(email="ui-matrix-staff@example.com", is_staff=True)
    project = create_project(
        owner=owner,
        name="UI Matrix Project",
        visibility=Project.Visibility.PUBLIC,
        public_comment_policy=Project.PublicCommentPolicy.AUTHENTICATED_USERS,
    )
    add_project_member(actor=owner, project=project, user=manager, role="manager")
    add_project_member(actor=owner, project=project, user=member, role="member")
    add_project_member(actor=owner, project=project, user=viewer, role="viewer")

    responses = {
        "owner": client.get(f"/api/v1/projects/{project.id}/", **auth_header(owner)),
        "manager": client.get(f"/api/v1/projects/{project.id}/", **auth_header(manager)),
        "member": client.get(f"/api/v1/projects/{project.id}/", **auth_header(member)),
        "viewer": client.get(f"/api/v1/projects/{project.id}/", **auth_header(viewer)),
        "outsider": client.get(f"/api/v1/projects/{project.id}/", **auth_header(outsider)),
        "staff": client.get(f"/api/v1/projects/{project.id}/", **auth_header(staff_user)),
    }
    capabilities = {
        role: response.json()["data"]["capabilities"] for role, response in responses.items()
    }

    assert all(response.status_code == 200 for response in responses.values())
    assert capabilities["owner"]["can_manage_members"] is True
    assert capabilities["owner"]["can_read_audit_log"] is True
    assert capabilities["manager"]["can_manage_members"] is False
    assert capabilities["manager"]["can_create_task"] is True
    assert capabilities["member"]["can_create_task"] is True
    assert capabilities["viewer"]["can_create_task"] is False
    assert capabilities["viewer"]["can_comment"] is True
    assert capabilities["viewer"]["can_upload_task_attachment"] is False
    assert capabilities["viewer"]["can_upload_comment_attachment"] is True
    assert capabilities["outsider"]["can_comment"] is True
    assert capabilities["outsider"]["can_upload_task_attachment"] is False
    assert capabilities["staff"]["can_schedule"] is True
    assert capabilities["staff"]["can_manage_members"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_closed_project_outputs_disable_task_write_capabilities(client):
    """Verify closed project output disables task-writing UI capabilities."""
    owner = create_user(email="ui-closed-owner@example.com")
    project = create_project(owner=owner, name="Closed UI Project")
    json_post(client, f"/api/v1/projects/{project.id}/close/", {}, owner)

    response = client.get(f"/api/v1/projects/{project.id}/", **auth_header(owner))

    assert response.status_code == 200
    assert response.json()["data"]["capabilities"]["can_close"] is False
    assert response.json()["data"]["capabilities"]["can_reopen"] is True
    assert response.json()["data"]["capabilities"]["can_create_task"] is False
    assert response.json()["data"]["capabilities"]["can_upload_task_attachment"] is False
    assert response.json()["data"]["capabilities"]["can_upload_comment_attachment"] is True


@pytest.mark.integration
@pytest.mark.django_db
def test_task_outputs_include_related_summaries_transitions_and_capabilities(client):
    """Verify task responses expose related summaries and workflow capability data."""
    owner = create_user(email="ui-task-owner@example.com")
    assignee = create_user(email="ui-task-assignee@example.com")
    project = create_project(owner=owner, name="UI Task Project")
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    task = create_task(actor=owner, project=project, assignee=assignee, title="UI Task")
    task.status = Task.Status.ACCEPTED
    task.save(update_fields=["status"])

    response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/",
        **auth_header(owner),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["project"] == {
        "id": project.id,
        "name": "UI Task Project",
        "state": "active",
        "visibility": "private",
    }
    assert data["assignee"] == user_summary(assignee)
    assert data["allowed_transitions"] == ["cancelled", "in_progress", "on_hold"]
    assert data["capabilities"] == {
        "can_update": True,
        "can_delete": True,
        "can_transition": True,
        "can_watch": False,
        "can_unwatch": True,
        "can_comment": True,
        "can_upload_attachment": True,
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_task_capabilities_role_matrix(client):
    """Verify task capabilities reflect writable roles, viewers, and public commenters."""
    owner = create_user(email="ui-task-matrix-owner@example.com")
    assignee = create_user(email="ui-task-matrix-assignee@example.com")
    viewer = create_user(email="ui-task-matrix-viewer@example.com")
    outsider = create_user(email="ui-task-matrix-outsider@example.com")
    project = create_project(
        owner=owner,
        name="UI Task Matrix Project",
        visibility=Project.Visibility.PUBLIC,
        public_comment_policy=Project.PublicCommentPolicy.AUTHENTICATED_USERS,
    )
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    add_project_member(actor=owner, project=project, user=viewer, role="viewer")
    task = create_task(actor=owner, project=project, assignee=assignee, title="Matrix Task")

    owner_response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/",
        **auth_header(owner),
    )
    viewer_response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/",
        **auth_header(viewer),
    )
    outsider_response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/",
        **auth_header(outsider),
    )

    owner_capabilities = owner_response.json()["data"]["capabilities"]
    viewer_capabilities = viewer_response.json()["data"]["capabilities"]
    outsider_capabilities = outsider_response.json()["data"]["capabilities"]

    assert owner_response.status_code == 200
    assert owner_capabilities["can_update"] is True
    assert owner_capabilities["can_unwatch"] is True
    assert viewer_response.status_code == 200
    assert viewer_capabilities["can_update"] is False
    assert viewer_capabilities["can_comment"] is True
    assert viewer_capabilities["can_watch"] is True
    assert viewer_capabilities["can_upload_attachment"] is False
    assert outsider_response.status_code == 200
    assert outsider_capabilities["can_update"] is False
    assert outsider_capabilities["can_comment"] is True
    assert outsider_capabilities["can_watch"] is False


@pytest.mark.integration
@pytest.mark.django_db
def test_comment_attachment_and_audit_outputs_include_ui_fields(client):
    """Verify comment, attachment, and audit responses expose UI contract fields."""
    owner = create_user(email="ui-contract-owner@example.com")
    assignee = create_user(email="ui-contract-assignee@example.com")
    project = create_project(owner=owner, name="UI Contract Project")
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    task = create_task(actor=owner, project=project, assignee=assignee, title="Contract Task")
    comment = create_comment(actor=assignee, task=task, body="Contract comment")
    file_obj = SimpleUploadedFile("contract.log", b"log", content_type="text/plain")
    upload_response = client.post(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/comments/{comment.id}/attachments/",
        {"file": file_obj},
        **auth_header(assignee),
    )

    comment_response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/comments/{comment.id}/",
        **auth_header(assignee),
    )
    attachment_id = upload_response.json()["data"]["id"]
    attachment_list_response = client.get(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/comments/{comment.id}/attachments/",
        **auth_header(owner),
    )
    audit_response = client.get(f"/api/v1/projects/{project.id}/audit-log/", **auth_header(owner))

    comment_data = comment_response.json()["data"]
    attachment_data = attachment_list_response.json()["data"][0]
    audit_item = next(
        item for item in audit_response.json()["data"] if item["actor_id"] == owner.id
    )

    assert upload_response.status_code == 201
    assert comment_response.status_code == 200
    assert comment_data["author"] == user_summary(assignee)
    assert comment_data["capabilities"] == {
        "can_update": True,
        "can_delete": True,
        "can_upload_attachment": True,
    }
    assert attachment_list_response.status_code == 200
    assert attachment_data["id"] == attachment_id
    assert attachment_data["uploaded_by"] == user_summary(assignee)
    assert attachment_data["capabilities"] == {
        "can_download": True,
        "can_delete": True,
    }
    assert audit_response.status_code == 200
    assert audit_item["actor"] == user_summary(owner)


@pytest.mark.integration
@pytest.mark.django_db
def test_project_attachment_limits_endpoint_returns_upload_metadata(client):
    """Verify project attachment limits expose settings and project usage."""
    owner = create_user(email="ui-limits-owner@example.com")
    assignee = create_user(email="ui-limits-assignee@example.com")
    project = create_project(owner=owner, name="UI Limits Project")
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    task = create_task(actor=owner, project=project, assignee=assignee)
    file_obj = SimpleUploadedFile("limits.txt", b"limit bytes", content_type="text/plain")
    client.post(
        f"/api/v1/projects/{project.id}/tasks/{task.id}/attachments/",
        {"file": file_obj},
        **auth_header(owner),
    )

    response = client.get(
        f"/api/v1/projects/{project.id}/attachments/limits/",
        **auth_header(owner),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["allowed_content_types"] == ["image/jpeg", "image/png", "text/plain"]
    assert data["allowed_text_extensions"] == [".err", ".log", ".out", ".txt"]
    assert data["max_file_size_bytes"] == 1_048_576
    assert data["max_project_bytes"] == 20_971_520
    assert data["project_used_bytes"] == len(b"limit bytes")
    assert data["project_remaining_bytes"] == 20_971_520 - len(b"limit bytes")


@pytest.mark.integration
@pytest.mark.django_db
def test_task_list_ui_contract_uses_batched_capability_queries(client):
    """Verify task UI capability fields avoid per-task query growth."""
    owner = create_user(email="ui-query-owner@example.com")
    assignee = create_user(email="ui-query-assignee@example.com")
    project = create_project(owner=owner, name="UI Query Project")
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    for index in range(6):
        create_task(
            actor=owner,
            project=project,
            assignee=assignee,
            title=f"Query Task {index}",
        )

    with CaptureQueriesContext(connection) as captured:
        response = client.get(f"/api/v1/projects/{project.id}/tasks/", **auth_header(owner))

    assert response.status_code == 200
    assert len(response.json()["data"]) == 6
    assert len(captured) <= 7


@pytest.mark.integration
@pytest.mark.django_db
def test_attachment_list_ui_contract_uses_batched_capability_queries(client):
    """Verify attachment UI capability fields avoid per-attachment query growth."""
    owner = create_user(email="ui-attachment-query-owner@example.com")
    assignee = create_user(email="ui-attachment-query-assignee@example.com")
    project = create_project(owner=owner, name="UI Attachment Query Project")
    add_project_member(actor=owner, project=project, user=assignee, role="member")
    task = create_task(actor=owner, project=project, assignee=assignee)
    for index in range(6):
        file_obj = SimpleUploadedFile(
            f"query-{index}.txt",
            f"attachment {index}".encode(),
            content_type="text/plain",
        )
        client.post(
            f"/api/v1/projects/{project.id}/tasks/{task.id}/attachments/",
            {"file": file_obj},
            **auth_header(owner),
        )

    with CaptureQueriesContext(connection) as captured:
        response = client.get(
            f"/api/v1/projects/{project.id}/tasks/{task.id}/attachments/",
            **auth_header(owner),
        )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 6
    assert len(captured) <= 7
