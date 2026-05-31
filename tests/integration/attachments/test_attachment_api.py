"""Integration tests for attachment API endpoints."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
)
from tests.integration.tasks.test_task_api import create_task


def upload_url(project_id, task_id):
    """Return the task attachment upload URL."""
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/attachments/"


@pytest.mark.integration
@pytest.mark.django_db
def test_task_attachment_upload_download_and_delete(client):
    """Verify task attachments can be uploaded, downloaded, and soft deleted."""
    owner = create_user("attachment-owner@example.com")
    assignee = create_user("attachment-assignee@example.com")
    project = create_project(client, owner, name="Attachment", visibility="private")
    add_member(client, owner, project["id"], assignee, role="member")
    task = create_task(client, owner, project["id"], assignee)
    file_obj = SimpleUploadedFile("screen.png", b"\x89PNG\r\n", content_type="image/png")

    upload_response = client.post(
        upload_url(project["id"], task["id"]),
        {"file": file_obj},
        **auth_header(owner),
    )
    attachment = upload_response.json()["data"]
    download_response = client.get(
        f"/api/v1/attachments/{attachment['id']}/download/",
        **auth_header(owner),
    )
    delete_response = client.delete(
        f"/api/v1/attachments/{attachment['id']}/",
        **auth_header(owner),
    )

    assert upload_response.status_code == 201
    assert attachment["original_filename"] == "screen.png"
    assert download_response.status_code == 200
    assert download_response.content == b"\x89PNG\r\n"
    assert delete_response.status_code == 204


@pytest.mark.integration
@pytest.mark.django_db
def test_task_attachment_rejects_viewer_upload(client):
    """Verify viewers cannot upload task attachments."""
    owner = create_user("attachment-owner-viewer@example.com")
    viewer = create_user("attachment-viewer@example.com")
    project = create_project(client, owner, name="Attachment Viewer", visibility="public")
    add_member(client, owner, project["id"], viewer, role="viewer")
    task = create_task(client, owner, project["id"], viewer)
    file_obj = SimpleUploadedFile("note.txt", b"log", content_type="text/plain")

    response = client.post(
        upload_url(project["id"], task["id"]),
        {"file": file_obj},
        **auth_header(viewer),
    )

    assert response.status_code == 403
    assert response.json()["errors"][0]["code"] == "permission_denied"
