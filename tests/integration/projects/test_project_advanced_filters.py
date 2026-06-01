"""Integration tests for advanced project list filtering."""

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone

from apps.projects.models import Project, ProjectMembership
from tests.factories import add_project_member, auth_header, create_project, create_user


def _project_filter_fixture():
    """Create projects that cover all project filter dimensions."""
    actor = create_user(email="project-filter-actor@example.com")
    other = create_user(email="project-filter-other@example.com")
    base_time = timezone.now()
    alpha = create_project(
        owner=actor,
        name="Alpha Private",
        visibility=Project.Visibility.PRIVATE,
    )
    bravo = create_project(
        owner=actor,
        name="Bravo Public",
        description="Release roadmap",
        visibility=Project.Visibility.PUBLIC,
    )
    charlie = create_project(
        owner=other,
        name="Charlie Public",
        visibility=Project.Visibility.PUBLIC,
    )
    secret = create_project(
        owner=other,
        name="Delta Secret",
        visibility=Project.Visibility.PRIVATE,
    )
    managed = create_project(
        owner=other,
        name="Managed CRM",
        visibility=Project.Visibility.PRIVATE,
    )
    closed = create_project(owner=actor, name="Closed Ops", visibility=Project.Visibility.PRIVATE)
    add_project_member(
        actor=other,
        project=managed,
        user=actor,
        role=ProjectMembership.Role.MANAGER,
    )
    Project.objects.filter(pk=closed.pk).update(
        state=Project.State.CLOSED,
        closed_at=base_time,
    )
    timestamps = {
        alpha.pk: base_time - timedelta(days=7),
        bravo.pk: base_time - timedelta(days=3),
        charlie.pk: base_time - timedelta(days=2),
        secret.pk: base_time - timedelta(days=1),
        managed.pk: base_time - timedelta(hours=12),
        closed.pk: base_time - timedelta(hours=1),
    }
    for project_id, timestamp in timestamps.items():
        Project.objects.filter(pk=project_id).update(created_at=timestamp, updated_at=timestamp)

    return {
        "actor": actor,
        "other": other,
        "base_time": base_time,
        "projects": {
            "alpha": alpha,
            "bravo": bravo,
            "charlie": charlie,
            "secret": secret,
            "managed": managed,
            "closed": closed,
        },
    }


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(
        query={"visibility": "public", "ordering": "name"},
        expected_names=["Bravo Public", "Charlie Public"],
    ),
    dict(query={"role": "manager", "ordering": "name"}, expected_names=["Managed CRM"]),
    dict(query={"state": "closed", "ordering": "name"}, expected_names=["Closed Ops"]),
    dict(query={"search": "crm", "ordering": "name"}, expected_names=["Managed CRM"]),
    dict(query={"q": "release", "ordering": "name"}, expected_names=["Bravo Public"]),
)
def test_project_list_supports_advanced_filters(client, query, expected_names):
    """Verify project filters return only matching visible projects."""
    data = _project_filter_fixture()

    response = client.get(
        f"/api/v1/projects/?{urlencode(query)}",
        **auth_header(data["actor"]),
    )

    assert response.status_code == 200
    assert [project["name"] for project in response.json()["data"]] == expected_names
    assert "Delta Secret" not in {project["name"] for project in response.json()["data"]}


@pytest.mark.integration
@pytest.mark.django_db
def test_project_list_filters_by_owner_and_created_range_without_leaking_private_projects(client):
    """Verify owner and date filters keep private projects access-scoped."""
    data = _project_filter_fixture()
    created_after = (data["base_time"] - timedelta(days=4)).isoformat()
    query = urlencode(
        {
            "owner_id": data["other"].id,
            "created_after": created_after,
            "ordering": "name",
        }
    )

    response = client.get(f"/api/v1/projects/?{query}", **auth_header(data["actor"]))

    assert response.status_code == 200
    assert [project["name"] for project in response.json()["data"]] == [
        "Charlie Public",
        "Managed CRM",
    ]


@pytest.mark.integration
@pytest.mark.django_db
def test_project_list_uses_stable_secondary_ordering(client):
    """Verify project ordering remains stable when primary values are equal."""
    actor = create_user(email="project-ordering@example.com")
    first = create_project(owner=actor, name="Same Name")
    second = create_project(owner=actor, name="Same Name")

    response = client.get("/api/v1/projects/?ordering=name", **auth_header(actor))

    assert response.status_code == 200
    assert [project["id"] for project in response.json()["data"][:2]] == [first.id, second.id]


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(query={"visibility": "internal"}, expected_field="visibility"),
    dict(query={"state": "archived"}, expected_field="state"),
    dict(query={"role": "admin"}, expected_field="role"),
    dict(query={"owner_id": "abc"}, expected_field="owner_id"),
    dict(query={"created_after": "not-a-date"}, expected_field="created_after"),
    dict(query={"ordering": "deleted_at"}, expected_field="ordering"),
)
def test_project_list_rejects_invalid_filter_values(client, query, expected_field):
    """Verify unsupported project filters return validation errors."""
    actor = create_user(email=f"project-invalid-{expected_field}@example.com")

    response = client.get(
        f"/api/v1/projects/?{urlencode(query)}",
        **auth_header(actor),
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == expected_field
