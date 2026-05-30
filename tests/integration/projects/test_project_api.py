"""Integration tests for project API endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken


def create_user(email, *, display_name=None, is_staff=False):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        email=email,
        password="StrongerPass123!",
        display_name=display_name or email.split("@")[0].title(),
        is_staff=is_staff,
    )


def auth_header(user):
    """Return an authorization header for a user."""
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def json_post(client, path, payload, user):
    """POST JSON as an authenticated user."""
    return client.post(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def json_patch(client, path, payload, user):
    """PATCH JSON as an authenticated user."""
    return client.patch(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def create_project(client, owner, *, name="CRM", visibility="private"):
    """Create a project through the API."""
    response = json_post(
        client,
        "/api/v1/projects/",
        {
            "name": name,
            "description": f"{name} work",
            "visibility": visibility,
        },
        owner,
    )
    assert response.status_code == 201
    return response.json()["data"]


def add_member(client, owner, project_id, user, role="member"):
    """Add a project member through the API."""
    response = json_post(
        client,
        f"/api/v1/projects/{project_id}/members/",
        {"user_id": user.id, "role": role},
        owner,
    )
    assert response.status_code == 201
    return response.json()["data"]


@pytest.mark.integration
@pytest.mark.django_db
def test_project_create_creates_owner_membership_and_audit_log(client):
    """Verify project creation creates owner membership and audit log."""
    owner = create_user("owner-create@example.com", display_name="Owner Create")

    project = create_project(client, owner, name="Create Project", visibility="private")

    from apps.audit.models import AuditLog
    from apps.projects.models import ProjectMembership

    owner_membership = ProjectMembership.objects.get(project_id=project["id"], user=owner)
    assert owner_membership.role == "owner"
    assert owner_membership.created_by == owner
    assert AuditLog.objects.filter(
        actor=owner,
        project_id=project["id"],
        action="project.created",
        entity_type="project",
        entity_id=project["id"],
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_project_list_visibility_and_anonymous_authentication(client):
    """Verify project list visibility for members, authenticated users, and anonymous users."""
    owner = create_user("owner-list@example.com")
    private_member = create_user("private-member@example.com")
    outsider = create_user("outsider-list@example.com")
    private_project = create_project(client, owner, name="Private Project", visibility="private")
    public_project = create_project(client, owner, name="Public Project", visibility="public")
    add_member(client, owner, private_project["id"], private_member, role="viewer")

    anonymous_response = client.get("/api/v1/projects/")
    member_response = client.get("/api/v1/projects/", **auth_header(private_member))
    outsider_response = client.get("/api/v1/projects/", **auth_header(outsider))

    assert anonymous_response.status_code == 401
    assert anonymous_response.json()["errors"][0]["code"] == "authentication_required"
    assert member_response.status_code == 200
    assert {project["id"] for project in member_response.json()["data"]} == {
        private_project["id"],
        public_project["id"],
    }
    assert outsider_response.status_code == 200
    assert [project["id"] for project in outsider_response.json()["data"]] == [public_project["id"]]


@pytest.mark.integration
@pytest.mark.django_db
def test_closed_public_project_remains_readable_to_authenticated_non_members(client):
    """Verify closed public projects stay readable for authenticated non-members."""
    owner = create_user("owner-closed-public@example.com")
    outsider = create_user("outsider-closed-public@example.com")
    project = create_project(client, owner, name="Closed Public Project", visibility="public")
    close_response = client.post(
        f"/api/v1/projects/{project['id']}/close/",
        data={},
        content_type="application/json",
        **auth_header(owner),
    )

    list_response = client.get("/api/v1/projects/", **auth_header(outsider))
    detail_response = client.get(f"/api/v1/projects/{project['id']}/", **auth_header(outsider))
    anonymous_detail_response = client.get(f"/api/v1/projects/{project['id']}/")

    assert close_response.status_code == 200
    assert list_response.status_code == 200
    assert project["id"] in [item["id"] for item in list_response.json()["data"]]
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == project["id"]
    assert detail_response.json()["data"]["state"] == "closed"
    assert anonymous_detail_response.status_code == 401
    assert anonymous_detail_response.json()["errors"][0]["code"] == "authentication_required"


@pytest.mark.integration
@pytest.mark.django_db
def test_project_filters_search_role_and_ordering(client):
    """Verify project list supports basic filters, search, role, and ordering."""
    owner = create_user("owner-filter@example.com")
    manager = create_user("manager-filter@example.com")
    create_project(client, owner, name="Zeta Internal", visibility="private")
    alpha_public = create_project(client, owner, name="Alpha Public", visibility="public")
    beta_public = create_project(client, owner, name="Beta Public", visibility="public")
    add_member(client, owner, beta_public["id"], manager, role="manager")

    visibility_response = client.get(
        "/api/v1/projects/?visibility=public&ordering=name",
        **auth_header(manager),
    )
    role_response = client.get("/api/v1/projects/?role=manager", **auth_header(manager))
    search_response = client.get("/api/v1/projects/?search=alpha", **auth_header(manager))

    assert visibility_response.status_code == 200
    assert [project["id"] for project in visibility_response.json()["data"]] == [
        alpha_public["id"],
        beta_public["id"],
    ]
    assert role_response.status_code == 200
    assert [project["id"] for project in role_response.json()["data"]] == [beta_public["id"]]
    assert search_response.status_code == 200
    assert [project["id"] for project in search_response.json()["data"]] == [alpha_public["id"]]


@pytest.mark.integration
@pytest.mark.django_db
def test_private_project_leak_policy_and_visible_forbidden_write(client):
    """Verify private inaccessible projects return 404 and visible writes return 403."""
    owner = create_user("owner-leak@example.com")
    outsider = create_user("outsider-leak@example.com")
    private_project = create_project(client, owner, name="Hidden Project", visibility="private")
    public_project = create_project(client, owner, name="Visible Project", visibility="public")

    hidden_response = client.get(
        f"/api/v1/projects/{private_project['id']}/",
        **auth_header(outsider),
    )
    forbidden_response = json_patch(
        client,
        f"/api/v1/projects/{public_project['id']}/",
        {"name": "Renamed by outsider"},
        outsider,
    )

    assert hidden_response.status_code == 404
    assert hidden_response.json()["errors"][0]["code"] == "not_found"
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["errors"][0]["code"] == "permission_denied"


@pytest.mark.integration
@pytest.mark.django_db
def test_soft_delete_project_removes_from_selectors_api_and_memberships(client):
    """Verify soft-deleted projects and memberships are hidden from selectors and API."""
    owner = create_user("owner-delete@example.com")
    member = create_user("member-delete@example.com")
    project = create_project(client, owner, name="Delete Project", visibility="private")
    add_member(client, owner, project["id"], member, role="member")

    delete_response = client.delete(f"/api/v1/projects/{project['id']}/", **auth_header(owner))
    detail_response = client.get(f"/api/v1/projects/{project['id']}/", **auth_header(owner))
    list_response = client.get("/api/v1/projects/", **auth_header(owner))

    from apps.projects.models import Project, ProjectMembership
    from apps.projects.selectors import visible_projects_for_user

    deleted_project = Project.objects.get(pk=project["id"])
    active_memberships = ProjectMembership.objects.filter(
        project=deleted_project, deleted_at__isnull=True
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert detail_response.status_code == 404
    assert project["id"] not in [item["id"] for item in list_response.json()["data"]]
    assert deleted_project.deleted_at is not None
    assert deleted_project.deleted_by == owner
    assert not active_memberships.exists()
    assert not visible_projects_for_user(owner).filter(pk=project["id"]).exists()
