"""End-to-end smoke flow against a running local API."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest


def assert_status(response: httpx.Response, expected_status: int) -> None:
    """Assert an HTTP response status and include the response body on failure."""
    assert response.status_code == expected_status, response.text


def post_json(client: httpx.Client, path: str, payload: dict, token: str | None = None):
    """POST JSON to the API with an optional bearer token."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(path, json=payload, headers=headers)


def register_user(client: httpx.Client, *, email: str, display_name: str) -> dict:
    """Register a user through the public API."""
    response = post_json(
        client,
        "/api/v1/users/register/",
        {
            "email": email,
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "display_name": display_name,
        },
    )
    assert_status(response, 201)
    return response.json()["data"]


def login_user(client: httpx.Client, *, email: str) -> str:
    """Log in a user and return the access token."""
    response = post_json(
        client,
        "/api/v1/users/token/",
        {"email": email, "password": "StrongPass123!"},
    )
    assert_status(response, 200)
    return response.json()["data"]["access"]


@pytest.mark.e2e
def test_register_project_task_comment_attachment_flow():
    """Verify the Docker Compose API supports the main cross-app user flow."""
    base_url = os.environ.get("E2E_BASE_URL")
    if not base_url:
        pytest.skip("E2E_BASE_URL must point to a running Docker Compose API.")

    suffix = uuid4().hex
    owner_email = f"e2e-owner-{suffix}@example.com"
    member_email = f"e2e-member-{suffix}@example.com"

    with httpx.Client(base_url=base_url, timeout=10) as client:
        register_user(client, email=owner_email, display_name="E2E Owner")
        member = register_user(client, email=member_email, display_name="E2E Member")
        owner_token = login_user(client, email=owner_email)
        member_token = login_user(client, email=member_email)

        project_response = post_json(
            client,
            "/api/v1/projects/",
            {
                "name": f"E2E Project {suffix}",
                "description": "Docker Compose smoke flow",
                "visibility": "private",
            },
            owner_token,
        )
        assert_status(project_response, 201)
        project = project_response.json()["data"]

        member_response = post_json(
            client,
            f"/api/v1/projects/{project['id']}/members/",
            {"user_id": member["id"], "role": "member"},
            owner_token,
        )
        assert_status(member_response, 201)

        task_response = post_json(
            client,
            f"/api/v1/projects/{project['id']}/tasks/",
            {"title": "E2E task", "assignee_id": member["id"]},
            owner_token,
        )
        assert_status(task_response, 201)
        task = task_response.json()["data"]

        transition_response = post_json(
            client,
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/transition/",
            {"status": "accepted"},
            member_token,
        )
        assert_status(transition_response, 200)

        comment_response = post_json(
            client,
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/comments/",
            {"body": "Verified from E2E"},
            member_token,
        )
        assert_status(comment_response, 201)
        comment = comment_response.json()["data"]

        upload_response = client.post(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}/comments/{comment['id']}/attachments/",
            files={"file": ("e2e.log", b"e2e smoke log", "text/plain")},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert_status(upload_response, 201)

        publish_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        schedule_response = client.put(
            f"/api/v1/projects/{project['id']}/publish-schedule/",
            json={"publish_at": publish_at},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert_status(schedule_response, 200)
