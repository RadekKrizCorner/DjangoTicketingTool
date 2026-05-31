"""Integration tests for attachment quotas."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.integration.projects.test_project_api import add_member, create_project, create_user
from tests.integration.tasks.test_task_api import create_task


@pytest.mark.integration
@pytest.mark.django_db
def test_attachment_larger_than_one_mb_is_rejected(client):
    """Verify oversized attachment uploads are rejected."""
    from tests.integration.projects.test_project_api import auth_header

    owner = create_user("quota-owner@example.com")
    assignee = create_user("quota-assignee@example.com")
    project = create_project(client, owner, name="Quota", visibility="private")
    add_member(client, owner, project["id"], assignee, role="member")
    task = create_task(client, owner, project["id"], assignee)
    file_obj = SimpleUploadedFile(
        "large.log",
        b"x" * (1024 * 1024 + 1),
        content_type="text/plain",
    )

    response = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/attachments/",
        {"file": file_obj},
        **auth_header(owner),
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "attachment_too_large"
