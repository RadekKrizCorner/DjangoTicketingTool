"""End-to-end flows against a running local Docker Compose API."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import pytest

PASSWORD = "StrongPass123!"


@pytest.fixture(scope="module")
def e2e_base_url() -> str:
    """Return the configured E2E API base URL or skip the test."""
    base_url = os.environ.get("E2E_BASE_URL")
    if not base_url:
        pytest.skip("E2E_BASE_URL must point to a running Docker Compose API.")
    return base_url.rstrip("/")


@pytest.fixture(scope="module")
def e2e_client(e2e_base_url: str) -> Iterator[httpx.Client]:
    """Return an HTTP client configured for the running E2E API."""
    with httpx.Client(
        base_url=e2e_base_url,
        headers=e2e_host_headers(e2e_base_url),
        timeout=10,
    ) as client:
        yield client


@pytest.fixture(scope="module")
def e2e_sessions(e2e_client: httpx.Client) -> dict[str, dict]:
    """Return reusable authenticated users for the E2E module."""
    suffix = uuid4().hex
    return {
        "owner": create_user_session(e2e_client, suffix=suffix, role="owner"),
        "member": create_user_session(e2e_client, suffix=suffix, role="member"),
        "outsider": create_user_session(e2e_client, suffix=suffix, role="outsider"),
    }


def bearer_headers(token: str | None) -> dict[str, str]:
    """Return bearer authorization headers when a token is provided."""
    if token is None:
        return {}
    return {"Authorization": f"Bearer {token}"}


def e2e_host_headers(base_url: str) -> dict[str, str]:
    """Return host headers needed for Docker bridge E2E requests."""
    host_header = os.environ.get("E2E_HOST_HEADER")
    if host_header is None and urlparse(base_url).hostname == "host.docker.internal":
        host_header = "localhost"
    if host_header is None:
        return {}
    return {"Host": host_header}


def assert_status(response: httpx.Response, expected_status: int) -> None:
    """Assert an HTTP response status and include the response body on failure."""
    assert response.status_code == expected_status, response.text


def assert_error(response: httpx.Response, expected_status: int, expected_code: str) -> None:
    """Assert an API error status and error code."""
    assert_status(response, expected_status)
    assert response.json()["errors"][0]["code"] == expected_code


def response_data(response: httpx.Response) -> dict:
    """Return the standard response data object."""
    return response.json()["data"]


def response_list(response: httpx.Response) -> list[dict]:
    """Return the standard response data list."""
    return response.json()["data"]


def post_json(
    client: httpx.Client,
    path: str,
    payload: dict,
    token: str | None = None,
) -> httpx.Response:
    """POST JSON to the API with an optional bearer token."""
    return client.post(path, json=payload, headers=bearer_headers(token))


def put_json(
    client: httpx.Client,
    path: str,
    payload: dict,
    token: str | None = None,
) -> httpx.Response:
    """PUT JSON to the API with an optional bearer token."""
    return client.put(path, json=payload, headers=bearer_headers(token))


def patch_json(
    client: httpx.Client,
    path: str,
    payload: dict,
    token: str | None = None,
) -> httpx.Response:
    """PATCH JSON to the API with an optional bearer token."""
    return client.patch(path, json=payload, headers=bearer_headers(token))


def register_user(client: httpx.Client, *, email: str, display_name: str) -> dict:
    """Register a user through the public API."""
    response = post_json(
        client,
        "/api/v1/users/register/",
        {
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "display_name": display_name,
        },
    )
    assert_status(response, 201)
    return response_data(response)


def login_user(client: httpx.Client, *, email: str) -> dict:
    """Log in a user and return the token payload."""
    response = post_json(
        client,
        "/api/v1/users/token/",
        {"email": email, "password": PASSWORD},
    )
    assert_status(response, 200)
    return response_data(response)


def create_user_session(client: httpx.Client, *, suffix: str, role: str) -> dict:
    """Create a unique user and return user data with JWT tokens."""
    email = f"e2e-{role}-{suffix}@example.com"
    user = register_user(client, email=email, display_name=f"E2E {role.title()}")
    tokens = login_user(client, email=email)
    return {"user": user, "access": tokens["access"], "refresh": tokens["refresh"]}


def create_project(
    client: httpx.Client,
    *,
    owner_token: str,
    suffix: str,
    name: str,
    visibility: str = "private",
    public_comment_policy: str = "members_only",
) -> dict:
    """Create a project through the API."""
    response = post_json(
        client,
        "/api/v1/projects/",
        {
            "name": f"{name} {suffix}",
            "description": f"{name} Docker Compose E2E",
            "visibility": visibility,
            "public_comment_policy": public_comment_policy,
        },
        owner_token,
    )
    assert_status(response, 201)
    return response_data(response)


def add_project_member(
    client: httpx.Client,
    *,
    owner_token: str,
    project_id: int,
    user_id: int,
    role: str,
) -> dict:
    """Add a user to a project through the API."""
    response = post_json(
        client,
        f"/api/v1/projects/{project_id}/members/",
        {"user_id": user_id, "role": role},
        owner_token,
    )
    assert_status(response, 201)
    return response_data(response)


def create_task(
    client: httpx.Client,
    *,
    token: str,
    project_id: int,
    title: str,
    assignee_id: int,
    description: str = "",
    priority: str = "medium",
    due_at: str | None = None,
) -> dict:
    """Create a project task through the API."""
    payload = {
        "title": title,
        "description": description,
        "assignee_id": assignee_id,
        "priority": priority,
    }
    if due_at is not None:
        payload["due_at"] = due_at
    response = post_json(client, f"/api/v1/projects/{project_id}/tasks/", payload, token)
    assert_status(response, 201)
    return response_data(response)


def create_comment(
    client: httpx.Client,
    *,
    token: str,
    project_id: int,
    task_id: int,
    body: str,
) -> dict:
    """Create a task comment through the API."""
    response = post_json(
        client,
        f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/",
        {"body": body},
        token,
    )
    assert_status(response, 201)
    return response_data(response)


def upload_comment_attachment(
    client: httpx.Client,
    *,
    token: str,
    project_id: int,
    task_id: int,
    comment_id: int,
    filename: str,
    content: bytes,
) -> dict:
    """Upload a text attachment to a task comment."""
    response = client.post(
        f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/attachments/",
        files={"file": (filename, content, "text/plain")},
        headers=bearer_headers(token),
    )
    assert_status(response, 201)
    return response_data(response)


def notification_types(items: list[dict]) -> set[str]:
    """Return notification type values from response items."""
    return {item["type"] for item in items}


@pytest.mark.e2e
def test_register_project_task_comment_attachment_flow(e2e_client, e2e_sessions):
    """Verify the Docker Compose API supports the main cross-app user flow."""
    suffix = uuid4().hex
    owner = e2e_sessions["owner"]
    member = e2e_sessions["member"]

    project = create_project(
        e2e_client,
        owner_token=owner["access"],
        suffix=suffix,
        name="Main Flow",
    )
    add_project_member(
        e2e_client,
        owner_token=owner["access"],
        project_id=project["id"],
        user_id=member["user"]["id"],
        role="member",
    )

    task = create_task(
        e2e_client,
        token=owner["access"],
        project_id=project["id"],
        title="E2E task",
        assignee_id=member["user"]["id"],
    )
    transition_response = post_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/transition/",
        {"status": "accepted"},
        member["access"],
    )
    assert_status(transition_response, 200)

    comment = create_comment(
        e2e_client,
        token=member["access"],
        project_id=project["id"],
        task_id=task["id"],
        body="Verified from E2E",
    )
    attachment = upload_comment_attachment(
        e2e_client,
        token=member["access"],
        project_id=project["id"],
        task_id=task["id"],
        comment_id=comment["id"],
        filename="e2e.log",
        content=b"e2e smoke log",
    )

    download_response = e2e_client.get(
        f"/api/v1/attachments/{attachment['id']}/download/",
        headers=bearer_headers(member["access"]),
    )
    assert_status(download_response, 200)
    assert download_response.content == b"e2e smoke log"

    notifications_response = e2e_client.get(
        "/api/v1/notifications/",
        headers=bearer_headers(member["access"]),
    )
    assert_status(notifications_response, 200)
    assert "task_assigned" in notification_types(response_list(notifications_response))

    read_all_response = post_json(
        e2e_client,
        "/api/v1/notifications/read-all/",
        {},
        member["access"],
    )
    assert_status(read_all_response, 200)
    assert response_data(read_all_response)["status"] == "read"

    publish_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    schedule_response = put_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/publish-schedule/",
        {"publish_at": publish_at},
        owner["access"],
    )
    assert_status(schedule_response, 200)


@pytest.mark.e2e
def test_public_endpoints_and_private_project_boundaries_flow(e2e_client, e2e_sessions):
    """Verify public endpoints work while concrete project data stays protected."""
    suffix = uuid4().hex
    owner = e2e_sessions["owner"]
    outsider = e2e_sessions["outsider"]

    live_response = e2e_client.get("/api/v1/health/live/")
    schema_response = e2e_client.get("/api/v1/schema/")
    docs_response = e2e_client.get("/api/v1/docs/")
    anonymous_projects_response = e2e_client.get("/api/v1/projects/")
    project = create_project(
        e2e_client,
        owner_token=owner["access"],
        suffix=suffix,
        name="Private Boundary",
    )
    outsider_private_detail = e2e_client.get(
        f"/api/v1/projects/{project['id']}/",
        headers=bearer_headers(outsider["access"]),
    )

    public_response = patch_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/",
        {"visibility": "public"},
        owner["access"],
    )
    outsider_public_detail = e2e_client.get(
        f"/api/v1/projects/{project['id']}/",
        headers=bearer_headers(outsider["access"]),
    )

    assert_status(live_response, 200)
    assert_status(schema_response, 200)
    assert_status(docs_response, 200)
    assert_error(anonymous_projects_response, 401, "authentication_required")
    assert_error(outsider_private_detail, 404, "not_found")
    assert_status(public_response, 200)
    assert_status(outsider_public_detail, 200)
    assert response_data(outsider_public_detail)["id"] == project["id"]


@pytest.mark.e2e
@pytest.mark.kwparametrize(
    dict(public_comment_policy="members_only", expected_status=403),
    dict(public_comment_policy="authenticated_users", expected_status=201),
)
def test_public_project_comment_policy_matrix(
    e2e_client,
    e2e_sessions,
    public_comment_policy,
    expected_status,
):
    """Verify public project comments follow the configured public comment policy."""
    suffix = uuid4().hex
    owner = e2e_sessions["owner"]
    member = e2e_sessions["member"]
    outsider = e2e_sessions["outsider"]
    project = create_project(
        e2e_client,
        owner_token=owner["access"],
        suffix=suffix,
        name="Public Comments",
        visibility="public",
        public_comment_policy=public_comment_policy,
    )
    add_project_member(
        e2e_client,
        owner_token=owner["access"],
        project_id=project["id"],
        user_id=member["user"]["id"],
        role="viewer",
    )
    task = create_task(
        e2e_client,
        token=owner["access"],
        project_id=project["id"],
        title="Comment policy task",
        assignee_id=member["user"]["id"],
    )

    response = post_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/comments/",
        {"body": f"Outsider comment for {public_comment_policy}"},
        outsider["access"],
    )

    assert_status(response, expected_status)
    if expected_status == 403:
        assert response.json()["errors"][0]["code"] == "permission_denied"
    else:
        assert response_data(response)["body"] == f"Outsider comment for {public_comment_policy}"


@pytest.mark.e2e
def test_personal_access_token_scope_and_revocation_flow(e2e_client, e2e_sessions):
    """Verify personal access tokens support script-style auth and scoped writes."""
    suffix = uuid4().hex
    owner = e2e_sessions["owner"]
    project = create_project(
        e2e_client,
        owner_token=owner["access"],
        suffix=suffix,
        name="PAT Scope",
    )

    read_token_response = post_json(
        e2e_client,
        "/api/v1/users/personal-tokens/",
        {"name": "E2E read token", "scopes": ["read_only"]},
        owner["access"],
    )
    full_token_response = post_json(
        e2e_client,
        "/api/v1/users/personal-tokens/",
        {"name": "E2E full token", "scopes": ["full_access"]},
        owner["access"],
    )
    assert_status(read_token_response, 201)
    assert_status(full_token_response, 201)
    read_token = response_data(read_token_response)
    full_token = response_data(full_token_response)

    read_me_response = e2e_client.get(
        "/api/v1/users/me/",
        headers=bearer_headers(read_token["token"]),
    )
    read_projects_response = e2e_client.get(
        "/api/v1/projects/",
        headers=bearer_headers(read_token["token"]),
    )
    denied_write_response = post_json(
        e2e_client,
        "/api/v1/projects/",
        {"name": f"Denied PAT {suffix}", "visibility": "private"},
        read_token["token"],
    )
    allowed_write_response = post_json(
        e2e_client,
        "/api/v1/projects/",
        {"name": f"Allowed PAT {suffix}", "visibility": "private"},
        full_token["token"],
    )
    revoke_response = e2e_client.delete(
        f"/api/v1/users/personal-tokens/{read_token['id']}/",
        headers=bearer_headers(owner["access"]),
    )
    revoked_read_response = e2e_client.get(
        f"/api/v1/projects/{project['id']}/",
        headers=bearer_headers(read_token["token"]),
    )

    assert_status(read_me_response, 200)
    assert response_data(read_me_response)["id"] == owner["user"]["id"]
    assert_status(read_projects_response, 200)
    assert project["id"] in {item["id"] for item in response_list(read_projects_response)}
    assert_error(denied_write_response, 403, "permission_denied")
    assert_status(allowed_write_response, 201)
    assert response_data(allowed_write_response)["name"] == f"Allowed PAT {suffix}"
    assert_status(revoke_response, 204)
    assert_error(revoked_read_response, 401, "token_not_valid")


@pytest.mark.e2e
def test_task_filters_notifications_and_closed_project_flow(e2e_client, e2e_sessions):
    """Verify task filters, notifications, closure, and reopen behavior over HTTP."""
    suffix = uuid4().hex
    owner = e2e_sessions["owner"]
    member = e2e_sessions["member"]
    reviewer = e2e_sessions["outsider"]
    project = create_project(
        e2e_client,
        owner_token=owner["access"],
        suffix=suffix,
        name="Task Filters",
    )
    add_project_member(
        e2e_client,
        owner_token=owner["access"],
        project_id=project["id"],
        user_id=member["user"]["id"],
        role="member",
    )
    add_project_member(
        e2e_client,
        owner_token=owner["access"],
        project_id=project["id"],
        user_id=reviewer["user"]["id"],
        role="viewer",
    )

    due_soon = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    due_later = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    bottleneck_task = create_task(
        e2e_client,
        token=owner["access"],
        project_id=project["id"],
        title=f"API bottleneck {suffix}",
        description="Investigate slow query path",
        assignee_id=member["user"]["id"],
        priority="urgent",
        due_at=due_soon,
    )
    create_task(
        e2e_client,
        token=owner["access"],
        project_id=project["id"],
        title=f"Docs draft {suffix}",
        description="Prepare reviewer notes",
        assignee_id=reviewer["user"]["id"],
        priority="low",
        due_at=due_later,
    )

    filtered_my_tasks = e2e_client.get(
        "/api/v1/tasks/my/",
        params={"q": suffix, "priority": "urgent", "ordering": "due_at"},
        headers=bearer_headers(member["access"]),
    )
    due_before = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    filtered_project_tasks = e2e_client.get(
        f"/api/v1/projects/{project['id']}/tasks/",
        params={"due_before": due_before, "ordering": "due_at"},
        headers=bearer_headers(owner["access"]),
    )
    member_notifications = e2e_client.get(
        "/api/v1/notifications/",
        headers=bearer_headers(member["access"]),
    )
    close_response = post_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/close/",
        {},
        owner["access"],
    )
    closed_create_response = post_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/tasks/",
        {"title": "Blocked after close", "assignee_id": member["user"]["id"]},
        owner["access"],
    )
    closed_update_response = patch_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/tasks/{bottleneck_task['id']}/",
        {"title": "Blocked title"},
        owner["access"],
    )
    reopen_response = post_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/reopen/",
        {},
        owner["access"],
    )
    reopened_update_response = patch_json(
        e2e_client,
        f"/api/v1/projects/{project['id']}/tasks/{bottleneck_task['id']}/",
        {"title": f"Reopened bottleneck {suffix}"},
        owner["access"],
    )

    assert_status(filtered_my_tasks, 200)
    assert [item["id"] for item in response_list(filtered_my_tasks)] == [bottleneck_task["id"]]
    assert_status(filtered_project_tasks, 200)
    assert [item["id"] for item in response_list(filtered_project_tasks)] == [
        bottleneck_task["id"]
    ]
    assert_status(member_notifications, 200)
    assert "task_assigned" in notification_types(response_list(member_notifications))
    assert_status(close_response, 200)
    assert response_data(close_response)["state"] == "closed"
    assert_error(closed_create_response, 409, "project_closed")
    assert_error(closed_update_response, 409, "project_closed")
    assert_status(reopen_response, 200)
    assert response_data(reopen_response)["state"] == "active"
    assert_status(reopened_update_response, 200)
    assert response_data(reopened_update_response)["title"] == f"Reopened bottleneck {suffix}"
