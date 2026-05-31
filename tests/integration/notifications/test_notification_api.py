"""Integration tests for notification API endpoints."""

import pytest

from tests.integration.projects.test_project_api import auth_header, create_user


@pytest.mark.integration
@pytest.mark.django_db
def test_notification_list_and_mark_read_are_user_scoped(client):
    """Verify users can list and mark only their own notifications."""
    from apps.notifications.services import create_notification

    owner = create_user("notification-owner@example.com")
    outsider = create_user("notification-outsider@example.com")
    notification = create_notification(
        user=owner,
        type="manual",
        title="Manual",
        message="Body",
        dedupe_key="manual:owner",
    )
    create_notification(
        user=outsider,
        type="manual",
        title="Other",
        message="Other body",
        dedupe_key="manual:outsider",
    )

    list_response = client.get("/api/v1/notifications/", **auth_header(owner))
    read_response = client.post(
        f"/api/v1/notifications/{notification.id}/read/",
        data={},
        content_type="application/json",
        **auth_header(owner),
    )
    outsider_read_response = client.post(
        f"/api/v1/notifications/{notification.id}/read/",
        data={},
        content_type="application/json",
        **auth_header(outsider),
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["data"]] == [notification.id]
    assert read_response.status_code == 200
    assert read_response.json()["data"]["read_at"] is not None
    assert outsider_read_response.status_code == 404
    assert outsider_read_response.json()["errors"][0]["code"] == "not_found"
