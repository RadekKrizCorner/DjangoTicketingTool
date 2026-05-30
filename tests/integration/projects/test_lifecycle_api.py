"""Integration tests for project lifecycle API endpoints."""

from datetime import timedelta

import pytest
from django.utils import timezone

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
)


def json_put(client, path, payload, user):
    """PUT JSON as an authenticated user."""
    return client.put(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def json_post(client, path, payload, user):
    """POST JSON as an authenticated user."""
    return client.post(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def iso_at(delta):
    """Return an aware ISO timestamp offset from now."""
    return (timezone.now() + delta).isoformat().replace("+00:00", "Z")


def naive_iso_at(delta):
    """Return a naive ISO timestamp offset from now."""
    return (timezone.now() + delta).replace(tzinfo=None).isoformat()


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(endpoint="publish-schedule", field="publish_at", value_kind="past", expected_status=400),
    dict(endpoint="publish-schedule", field="publish_at", value_kind="naive", expected_status=400),
    dict(endpoint="publish-schedule", field="publish_at", value_kind="future", expected_status=200),
    dict(endpoint="close-schedule", field="close_at", value_kind="past", expected_status=400),
    dict(endpoint="close-schedule", field="close_at", value_kind="naive", expected_status=400),
    dict(endpoint="close-schedule", field="close_at", value_kind="future", expected_status=200),
)
def test_schedule_publish_close_validation_matrix(
    client,
    endpoint,
    field,
    value_kind,
    expected_status,
):
    """Verify schedule endpoints validate past, naive, and future timestamps."""
    owner = create_user(f"owner-{endpoint}-{value_kind}@example.com")
    project = create_project(client, owner, name=f"{endpoint} {value_kind}", visibility="private")
    values = {
        "past": iso_at(timedelta(minutes=-5)),
        "naive": naive_iso_at(timedelta(hours=2)),
        "future": iso_at(timedelta(hours=2)),
    }

    response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/{endpoint}/",
        {field: values[value_kind]},
        owner,
    )

    assert response.status_code == expected_status
    if expected_status == 400:
        assert response.json()["errors"][0]["code"] == "invalid_schedule"


@pytest.mark.integration
@pytest.mark.django_db
def test_close_schedule_before_publish_schedule_is_invalid(client):
    """Verify close schedule must be after publish schedule when both are set."""
    owner = create_user("owner-close-before-publish@example.com")
    project = create_project(client, owner, name="Close Before Publish", visibility="private")
    publish_response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/publish-schedule/",
        {"publish_at": iso_at(timedelta(days=2))},
        owner,
    )

    close_response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/close-schedule/",
        {"close_at": iso_at(timedelta(days=1))},
        owner,
    )

    assert publish_response.status_code == 200
    assert close_response.status_code == 400
    assert close_response.json()["errors"][0]["code"] == "invalid_schedule"


@pytest.mark.integration
@pytest.mark.django_db
def test_schedule_cancel_only_clears_pending_schedule(client):
    """Verify schedule cancellation only clears pending schedule fields."""
    owner = create_user("owner-schedule-cancel@example.com")
    project = create_project(client, owner, name="Schedule Cancel", visibility="private")
    publish_response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/publish-schedule/",
        {"publish_at": iso_at(timedelta(days=1))},
        owner,
    )
    cancel_publish_response = client.delete(
        f"/api/v1/projects/{project['id']}/publish-schedule/",
        **auth_header(owner),
    )
    close_response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/close-schedule/",
        {"close_at": iso_at(timedelta(days=3))},
        owner,
    )
    cancel_close_response = client.delete(
        f"/api/v1/projects/{project['id']}/close-schedule/",
        **auth_header(owner),
    )
    detail_response = client.get(f"/api/v1/projects/{project['id']}/", **auth_header(owner))
    detail = detail_response.json()["data"]

    assert publish_response.status_code == 200
    assert cancel_publish_response.status_code == 204
    assert close_response.status_code == 200
    assert cancel_close_response.status_code == 204
    assert detail["publish_at"] is None
    assert detail["published_at"] is None
    assert detail["close_at"] is None
    assert detail["closed_at"] is None
    assert detail["visibility"] == "private"
    assert detail["state"] == "active"


@pytest.mark.integration
@pytest.mark.django_db
def test_close_reopen_state_conflicts(client):
    """Verify close and reopen enforce active and closed states."""
    owner = create_user("owner-close-reopen@example.com")
    project = create_project(client, owner, name="Close Reopen", visibility="private")

    close_response = json_post(client, f"/api/v1/projects/{project['id']}/close/", {}, owner)
    close_again_response = json_post(client, f"/api/v1/projects/{project['id']}/close/", {}, owner)
    reopen_response = json_post(client, f"/api/v1/projects/{project['id']}/reopen/", {}, owner)
    reopen_again_response = json_post(
        client,
        f"/api/v1/projects/{project['id']}/reopen/",
        {},
        owner,
    )

    assert close_response.status_code == 200
    assert close_response.json()["data"]["state"] == "closed"
    assert close_response.json()["data"]["closed_at"] is not None
    assert close_response.json()["data"]["close_at"] is None
    assert close_again_response.status_code == 409
    assert close_again_response.json()["errors"][0]["code"] == "conflict"
    assert reopen_response.status_code == 200
    assert reopen_response.json()["data"]["state"] == "active"
    assert reopen_response.json()["data"]["closed_at"] is None
    assert reopen_again_response.status_code == 409
    assert reopen_again_response.json()["errors"][0]["code"] == "conflict"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(role="manager", endpoint="close"),
    dict(role="manager", endpoint="reopen"),
    dict(role="member", endpoint="close"),
    dict(role="member", endpoint="reopen"),
    dict(role="viewer", endpoint="close"),
    dict(role="viewer", endpoint="reopen"),
)
def test_non_owner_members_cannot_close_or_reopen(client, role, endpoint):
    """Verify non-owner project members cannot close or reopen projects."""
    owner = create_user(f"owner-{role}-{endpoint}@example.com")
    actor = create_user(f"actor-{role}-{endpoint}@example.com")
    project = create_project(client, owner, name=f"{role} {endpoint}", visibility="public")
    add_member(client, owner, project["id"], actor, role=role)
    if endpoint == "reopen":
        close_response = json_post(client, f"/api/v1/projects/{project['id']}/close/", {}, owner)
        assert close_response.status_code == 200

    response = json_post(client, f"/api/v1/projects/{project['id']}/{endpoint}/", {}, actor)

    assert response.status_code == 403
    assert response.json()["errors"][0]["code"] == "permission_denied"


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_can_schedule_close_and_reopen_visible_project(client):
    """Verify staff can manage lifecycle without project membership."""
    owner = create_user("owner-staff-lifecycle@example.com")
    staff = create_user("staff-lifecycle@example.com", is_staff=True)
    project = create_project(client, owner, name="Staff Lifecycle", visibility="public")

    schedule_response = json_put(
        client,
        f"/api/v1/projects/{project['id']}/publish-schedule/",
        {"publish_at": iso_at(timedelta(days=1))},
        staff,
    )
    close_response = json_post(client, f"/api/v1/projects/{project['id']}/close/", {}, staff)
    reopen_response = json_post(client, f"/api/v1/projects/{project['id']}/reopen/", {}, staff)

    assert schedule_response.status_code == 200
    assert close_response.status_code == 200
    assert reopen_response.status_code == 200
