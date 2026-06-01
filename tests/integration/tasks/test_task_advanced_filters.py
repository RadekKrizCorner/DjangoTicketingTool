"""Integration tests for advanced task list filtering."""

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.utils import timezone

from apps.projects.models import ProjectMembership
from apps.tasks.models import Task
from tests.factories import (
    add_project_member,
    auth_header,
    create_project,
    create_task,
    create_user,
)


def _task_filter_fixture():
    """Create tasks that cover all task filter dimensions."""
    owner = create_user(email="task-filter-owner@example.com")
    member = create_user(email="task-filter-member@example.com")
    reviewer = create_user(email="task-filter-reviewer@example.com")
    project = create_project(owner=owner, name="Task Filter Project")
    add_project_member(
        actor=owner,
        project=project,
        user=member,
        role=ProjectMembership.Role.MEMBER,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=reviewer,
        role=ProjectMembership.Role.MEMBER,
    )
    base_time = timezone.now()
    build_api = create_task(
        actor=owner,
        project=project,
        assignee=member,
        title="Build API",
        description="Search endpoint implementation",
    )
    fix_incident = create_task(
        actor=owner,
        project=project,
        assignee=owner,
        title="Fix Incident",
        description="Payment bottleneck analysis",
    )
    write_docs = create_task(
        actor=owner,
        project=project,
        assignee=reviewer,
        title="Write Docs",
        description="Reviewer handbook",
    )
    Task.objects.filter(pk=build_api.pk).update(
        status=Task.Status.ACCEPTED,
        priority=Task.Priority.HIGH,
        due_at=base_time + timedelta(days=2),
        created_at=base_time - timedelta(days=5),
        updated_at=base_time - timedelta(days=5),
    )
    Task.objects.filter(pk=fix_incident.pk).update(
        status=Task.Status.IN_PROGRESS,
        priority=Task.Priority.URGENT,
        due_at=base_time + timedelta(days=1),
        created_at=base_time - timedelta(days=2),
        updated_at=base_time - timedelta(days=2),
    )
    Task.objects.filter(pk=write_docs.pk).update(
        status=Task.Status.COMPLETED,
        priority=Task.Priority.LOW,
        due_at=base_time + timedelta(days=5),
        created_at=base_time - timedelta(hours=6),
        updated_at=base_time - timedelta(hours=6),
    )

    return {
        "owner": owner,
        "member": member,
        "reviewer": reviewer,
        "project": project,
        "base_time": base_time,
        "tasks": {
            "build_api": build_api,
            "fix_incident": fix_incident,
            "write_docs": write_docs,
        },
    }


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(query={"status": "accepted", "ordering": "title"}, expected_titles=["Build API"]),
    dict(query={"priority": "urgent", "ordering": "title"}, expected_titles=["Fix Incident"]),
    dict(query={"search": "endpoint", "ordering": "title"}, expected_titles=["Build API"]),
    dict(query={"q": "payment", "ordering": "title"}, expected_titles=["Fix Incident"]),
)
def test_project_task_list_supports_advanced_filters(client, query, expected_titles):
    """Verify project task filters return matching visible tasks."""
    data = _task_filter_fixture()

    response = client.get(
        f"/api/v1/projects/{data['project'].id}/tasks/?{urlencode(query)}",
        **auth_header(data["owner"]),
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["data"]] == expected_titles


@pytest.mark.integration
@pytest.mark.django_db
def test_project_task_list_filters_by_assignee_and_due_range(client):
    """Verify assignee and due filters can be combined."""
    data = _task_filter_fixture()
    due_before = (data["base_time"] + timedelta(days=3)).isoformat()
    query = urlencode(
        {
            "assignee_id": data["member"].id,
            "due_before": due_before,
            "ordering": "due_at",
        }
    )

    response = client.get(
        f"/api/v1/projects/{data['project'].id}/tasks/?{query}",
        **auth_header(data["owner"]),
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["data"]] == ["Build API"]


@pytest.mark.integration
@pytest.mark.django_db
def test_my_tasks_endpoint_reuses_advanced_filters(client):
    """Verify personal task lists support the same task filters."""
    data = _task_filter_fixture()
    created_after = (data["base_time"] - timedelta(days=3)).isoformat()
    query = urlencode({"created_after": created_after, "ordering": "due_at"})

    response = client.get(f"/api/v1/tasks/my/?{query}", **auth_header(data["owner"]))

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["data"]] == ["Fix Incident"]


@pytest.mark.integration
@pytest.mark.django_db
def test_task_list_uses_stable_secondary_ordering(client):
    """Verify task ordering remains stable when primary values are equal."""
    owner = create_user(email="task-ordering@example.com")
    project = create_project(owner=owner)
    first = create_task(actor=owner, project=project, assignee=owner, title="Same Title")
    second = create_task(actor=owner, project=project, assignee=owner, title="Same Title")

    response = client.get(
        f"/api/v1/projects/{project.id}/tasks/?ordering=title",
        **auth_header(owner),
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()["data"][:2]] == [first.id, second.id]


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(query={"status": "blocked"}, expected_field="status"),
    dict(query={"priority": "critical"}, expected_field="priority"),
    dict(query={"assignee_id": "abc"}, expected_field="assignee_id"),
    dict(query={"due_after": "not-a-date"}, expected_field="due_after"),
    dict(query={"ordering": "project_id"}, expected_field="ordering"),
)
def test_task_list_rejects_invalid_filter_values(client, query, expected_field):
    """Verify unsupported task filters return validation errors."""
    owner = create_user(email=f"task-invalid-{expected_field}@example.com")
    project = create_project(owner=owner)

    response = client.get(
        f"/api/v1/projects/{project.id}/tasks/?{urlencode(query)}",
        **auth_header(owner),
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == expected_field
