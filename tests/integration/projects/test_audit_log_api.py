"""Integration tests for project audit log API endpoints."""

import pytest

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
)


@pytest.mark.integration
@pytest.mark.django_db
def test_audit_log_endpoint_is_owner_only(client):
    """Verify only the owner can read visible project audit logs."""
    owner = create_user("owner-audit@example.com")
    member = create_user("member-audit@example.com")
    outsider = create_user("outsider-audit@example.com")
    project = create_project(client, owner, name="Audit Project", visibility="public")
    add_member(client, owner, project["id"], member, role="manager")

    owner_response = client.get(
        f"/api/v1/projects/{project['id']}/audit-log/",
        **auth_header(owner),
    )
    member_response = client.get(
        f"/api/v1/projects/{project['id']}/audit-log/",
        **auth_header(member),
    )
    outsider_response = client.get(
        f"/api/v1/projects/{project['id']}/audit-log/",
        **auth_header(outsider),
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["data"][0]["action"] == "membership.added"
    assert any(item["action"] == "project.created" for item in owner_response.json()["data"])
    assert member_response.status_code == 403
    assert member_response.json()["errors"][0]["code"] == "permission_denied"
    assert outsider_response.status_code == 403
    assert outsider_response.json()["errors"][0]["code"] == "permission_denied"


@pytest.mark.integration
@pytest.mark.django_db
def test_private_audit_log_leak_policy_returns_not_found(client):
    """Verify private project audit logs are hidden from non-members."""
    owner = create_user("owner-private-audit@example.com")
    outsider = create_user("outsider-private-audit@example.com")
    project = create_project(client, owner, name="Private Audit", visibility="private")

    response = client.get(
        f"/api/v1/projects/{project['id']}/audit-log/",
        **auth_header(outsider),
    )

    assert response.status_code == 404
    assert response.json()["errors"][0]["code"] == "not_found"


@pytest.mark.integration
@pytest.mark.django_db
def test_audit_log_records_membership_and_lifecycle_actions(client):
    """Verify membership and lifecycle actions are written to audit logs."""
    owner = create_user("owner-audit-actions@example.com")
    member = create_user("member-audit-actions@example.com")
    project = create_project(client, owner, name="Audit Actions", visibility="public")
    add_member(client, owner, project["id"], member, role="viewer")
    close_response = client.post(
        f"/api/v1/projects/{project['id']}/close/",
        data={},
        content_type="application/json",
        **auth_header(owner),
    )

    response = client.get(f"/api/v1/projects/{project['id']}/audit-log/", **auth_header(owner))
    actions = [item["action"] for item in response.json()["data"]]

    assert close_response.status_code == 200
    assert response.status_code == 200
    assert actions == ["project.closed", "membership.added", "project.created"]
