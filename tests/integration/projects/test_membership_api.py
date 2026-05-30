"""Integration tests for project membership API endpoints."""

import pytest

from tests.integration.projects.test_project_api import (
    add_member,
    auth_header,
    create_project,
    create_user,
    json_patch,
    json_post,
)


def member_url(project_id, membership_id=None):
    """Return the members endpoint URL."""
    if membership_id is None:
        return f"/api/v1/projects/{project_id}/members/"
    return f"/api/v1/projects/{project_id}/members/{membership_id}/"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(role="owner", action="add", expected_status=201),
    dict(role="owner", action="update", expected_status=200),
    dict(role="owner", action="remove", expected_status=204),
    dict(role="manager", action="add", expected_status=403),
    dict(role="manager", action="update", expected_status=403),
    dict(role="manager", action="remove", expected_status=403),
    dict(role="member", action="add", expected_status=403),
    dict(role="member", action="update", expected_status=403),
    dict(role="member", action="remove", expected_status=403),
    dict(role="viewer", action="add", expected_status=403),
    dict(role="viewer", action="update", expected_status=403),
    dict(role="viewer", action="remove", expected_status=403),
)
def test_owner_only_member_management_matrix(client, role, action, expected_status):
    """Verify only project owners can add, update, or remove memberships."""
    owner = create_user(f"owner-{role}-{action}@example.com")
    actor = owner if role == "owner" else create_user(f"actor-{role}-{action}@example.com")
    target = create_user(f"target-{role}-{action}@example.com")
    other = create_user(f"other-{role}-{action}@example.com")
    project = create_project(client, owner, name=f"{role} {action}", visibility="public")
    target_membership = add_member(client, owner, project["id"], target, role="viewer")
    if role != "owner":
        add_member(client, owner, project["id"], actor, role=role)

    if action == "add":
        response = json_post(
            client,
            member_url(project["id"]),
            {"user_id": other.id, "role": "member"},
            actor,
        )
    elif action == "update":
        response = json_patch(
            client,
            member_url(project["id"], target_membership["id"]),
            {"role": "manager"},
            actor,
        )
    else:
        response = client.delete(
            member_url(project["id"], target_membership["id"]),
            **auth_header(actor),
        )

    assert response.status_code == expected_status


@pytest.mark.integration
@pytest.mark.django_db
def test_active_membership_uniqueness_and_soft_deleted_restore(client):
    """Verify duplicate active memberships conflict and soft-deleted rows restore."""
    owner = create_user("owner-restore@example.com")
    user = create_user("restore-member@example.com")
    project = create_project(client, owner, name="Restore Project", visibility="private")
    membership = add_member(client, owner, project["id"], user, role="viewer")

    duplicate_response = json_post(
        client,
        member_url(project["id"]),
        {"user_id": user.id, "role": "manager"},
        owner,
    )
    delete_response = client.delete(
        member_url(project["id"], membership["id"]), **auth_header(owner)
    )
    restored_response = json_post(
        client,
        member_url(project["id"]),
        {"user_id": user.id, "role": "manager"},
        owner,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["errors"][0]["code"] == "duplicate_membership"
    assert delete_response.status_code == 204
    assert restored_response.status_code == 201
    assert restored_response.json()["data"]["id"] == membership["id"]
    assert restored_response.json()["data"]["role"] == "manager"


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_removal_forbidden_and_transfer_updates_roles(client):
    """Verify owner cannot be removed without ownership transfer."""
    owner = create_user("owner-transfer@example.com")
    new_owner = create_user("new-owner-transfer@example.com")
    project = create_project(client, owner, name="Transfer Project", visibility="private")
    new_owner_membership = add_member(client, owner, project["id"], new_owner, role="member")
    members_response = client.get(member_url(project["id"]), **auth_header(owner))
    owner_membership = next(
        item for item in members_response.json()["data"] if item["user_id"] == owner.id
    )

    delete_owner_response = client.delete(
        member_url(project["id"], owner_membership["id"]),
        **auth_header(owner),
    )
    transfer_response = json_post(
        client,
        f"/api/v1/projects/{project['id']}/ownership-transfer/",
        {"new_owner_id": new_owner.id},
        owner,
    )

    from apps.projects.models import Project, ProjectMembership

    refreshed_project = Project.objects.get(pk=project["id"])
    old_owner_membership = ProjectMembership.objects.get(pk=owner_membership["id"])
    refreshed_new_owner_membership = ProjectMembership.objects.get(pk=new_owner_membership["id"])

    assert delete_owner_response.status_code == 400
    assert delete_owner_response.json()["errors"][0]["code"] == "owner_required"
    assert transfer_response.status_code == 200
    assert refreshed_project.owner == new_owner
    assert old_owner_membership.role == "manager"
    assert refreshed_new_owner_membership.role == "owner"


@pytest.mark.integration
@pytest.mark.django_db
def test_transfer_restores_soft_deleted_new_owner_membership(client):
    """Verify ownership transfer restores a deleted membership for the new owner."""
    owner = create_user("owner-transfer-restore@example.com")
    new_owner = create_user("new-owner-transfer-restore@example.com")
    project = create_project(client, owner, name="Transfer Restore", visibility="private")
    membership = add_member(client, owner, project["id"], new_owner, role="viewer")
    delete_response = client.delete(
        member_url(project["id"], membership["id"]), **auth_header(owner)
    )

    transfer_response = json_post(
        client,
        f"/api/v1/projects/{project['id']}/ownership-transfer/",
        {"new_owner_id": new_owner.id},
        owner,
    )

    from apps.projects.models import ProjectMembership

    restored_membership = ProjectMembership.objects.get(pk=membership["id"])

    assert delete_response.status_code == 204
    assert transfer_response.status_code == 200
    assert restored_membership.deleted_at is None
    assert restored_membership.role == "owner"
