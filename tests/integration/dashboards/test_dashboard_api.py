"""Integration tests for configurable dashboard APIs."""

import pytest
from django.utils import timezone

from apps.tasks.models import Task
from tests.factories import (
    add_project_member,
    auth_header,
    create_project,
    create_task,
    create_user,
)


def json_request(client, method: str, path: str, payload: dict, user):
    """Send an authenticated JSON request."""
    return getattr(client, method)(
        path,
        data=payload,
        content_type="application/json",
        **auth_header(user),
    )


def create_dashboard_response(client, *, user, name: str = "Operations Dashboard"):
    """Create a dashboard through the API."""
    return json_request(client, "post", "/api/v1/dashboards/", {"name": name}, user)


def add_widget_response(client, *, user, dashboard_id: int, payload: dict):
    """Create a dashboard widget through the API."""
    return json_request(
        client,
        "post",
        f"/api/v1/dashboards/{dashboard_id}/widgets/",
        payload,
        user,
    )


def share_dashboard_response(client, *, user, dashboard_id: int, shares: list[dict]):
    """Replace dashboard shares through the API."""
    return json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/shares/",
        {"shares": shares},
        user,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_can_create_dashboard_with_widgets_and_render(client):
    """Verify owner can create and render a dashboard."""
    owner = create_user(email="dashboard-owner@example.com")
    technician = create_user(email="dashboard-tech@example.com")
    project = create_project(owner=owner, name="Dashboard Project")
    add_project_member(actor=owner, project=project, user=technician, role="member")
    task = create_task(
        actor=owner,
        project=project,
        assignee=technician,
        title="Dashboard Task",
        priority=Task.Priority.URGENT,
    )
    task.status = Task.Status.IN_PROGRESS
    task.save(update_fields=["status"])

    create_response = create_dashboard_response(client, user=owner)
    dashboard_id = create_response.json()["data"]["id"]
    widget_response = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "Open tickets",
            "config": {
                "project_ids": [project.id],
                "statuses": [Task.Status.IN_PROGRESS],
            },
            "x": 0,
            "y": 0,
            "w": 3,
            "h": 2,
            "order": 1,
        },
    )
    render_response = json_request(
        client,
        "post",
        f"/api/v1/dashboards/{dashboard_id}/render/",
        {"filters": {}},
        owner,
    )

    assert create_response.status_code == 201
    assert widget_response.status_code == 201
    assert render_response.status_code == 200
    widget = render_response.json()["data"]["widgets"][0]
    assert widget["type"] == "metric_tile"
    assert widget["result"]["value"] == 1
    assert widget["drilldown"] == {
        "type": "task_list",
        "filters": {
            "project_ids": [project.id],
            "statuses": [Task.Status.IN_PROGRESS],
        },
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_dynamic_project_member_share_grants_and_revokes_access(client):
    """Verify project share follows current membership."""
    owner = create_user(email="dynamic-share-owner@example.com")
    member = create_user(email="dynamic-share-member@example.com")
    project = create_project(owner=owner, name="Dynamic Share Project")
    membership = add_project_member(actor=owner, project=project, user=member, role="member")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]

    share_response = share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[
            {
                "target_type": "project_members",
                "project_id": project.id,
                "access": "viewer",
            }
        ],
    )
    member_response = client.get(f"/api/v1/dashboards/{dashboard_id}/", **auth_header(member))
    membership.deleted_at = timezone.now()
    membership.deleted_by = owner
    membership.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
    revoked_response = client.get(f"/api/v1/dashboards/{dashboard_id}/", **auth_header(member))

    assert share_response.status_code == 200
    assert member_response.status_code == 200
    assert revoked_response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_only_share_management_and_editor_layout_access(client):
    """Verify owner manages shares while editor can save layout."""
    owner = create_user(email="editor-owner@example.com")
    editor = create_user(email="editor-user@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "All tickets",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 3,
            "h": 2,
            "order": 1,
        },
    ).json()["data"]["id"]
    share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[{"target_type": "user", "user_id": editor.id, "access": "editor"}],
    )

    editor_layout_response = json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/layout/",
        {"widgets": [{"id": widget_id, "x": 3, "y": 0, "w": 4, "h": 2, "order": 1}]},
        editor,
    )
    editor_share_response = share_dashboard_response(
        client,
        user=editor,
        dashboard_id=dashboard_id,
        shares=[],
    )

    assert editor_layout_response.status_code == 200
    assert editor_layout_response.json()["data"]["widgets"][0]["x"] == 3
    assert editor_share_response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
def test_owner_keeps_dashboard_list_access_after_removing_shares(client):
    """Verify deleted shares do not hide an owner's dashboard list row."""
    owner = create_user(email="share-removal-owner@example.com")
    viewer = create_user(email="share-removal-viewer@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[{"target_type": "user", "user_id": viewer.id, "access": "viewer"}],
    )

    remove_response = share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[],
    )
    list_response = client.get("/api/v1/dashboards/", **auth_header(owner))

    assert remove_response.status_code == 200
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["data"]] == [dashboard_id]


@pytest.mark.integration
@pytest.mark.django_db
def test_viewer_cannot_edit_dashboard_widgets_or_layout(client):
    """Verify viewer access is read-only."""
    owner = create_user(email="viewer-owner@example.com")
    viewer = create_user(email="viewer-user@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[{"target_type": "user", "user_id": viewer.id, "access": "viewer"}],
    )

    add_response = add_widget_response(
        client,
        user=viewer,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "All tickets",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 3,
            "h": 2,
            "order": 1,
        },
    )
    layout_response = json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/layout/",
        {"widgets": []},
        viewer,
    )

    assert add_response.status_code == 403
    assert layout_response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
def test_render_filters_widget_data_by_viewer_permissions(client):
    """Verify widget results only include visible task data."""
    owner = create_user(email="permission-owner@example.com")
    viewer = create_user(email="permission-viewer@example.com")
    visible_project = create_project(owner=owner, name="Visible Widget Project")
    hidden_project = create_project(owner=owner, name="Hidden Widget Project")
    add_project_member(actor=owner, project=visible_project, user=viewer, role="viewer")
    create_task(actor=owner, project=visible_project, assignee=owner, title="Visible Task")
    create_task(actor=owner, project=hidden_project, assignee=owner, title="Hidden Task")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "All tickets",
            "config": {"project_ids": [visible_project.id, hidden_project.id]},
            "x": 0,
            "y": 0,
            "w": 3,
            "h": 2,
            "order": 1,
        },
    )
    share_dashboard_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        shares=[{"target_type": "user", "user_id": viewer.id, "access": "viewer"}],
    )

    render_response = json_request(
        client,
        "post",
        f"/api/v1/dashboards/{dashboard_id}/render/",
        {"filters": {}},
        viewer,
    )

    assert render_response.status_code == 200
    assert render_response.json()["data"]["widgets"][0]["result"]["value"] == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_layout_rejects_overlapping_widgets(client):
    """Verify invalid grid layout is rejected."""
    owner = create_user(email="layout-owner@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    first_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "First",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 1,
        },
    ).json()["data"]["id"]
    second_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "Second",
            "config": {},
            "x": 4,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 2,
        },
    ).json()["data"]["id"]

    response = json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/layout/",
        {
            "widgets": [
                {"id": first_widget_id, "x": 0, "y": 0, "w": 4, "h": 2, "order": 1},
                {"id": second_widget_id, "x": 3, "y": 1, "w": 4, "h": 2, "order": 2},
            ]
        },
        owner,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "layout"


@pytest.mark.integration
@pytest.mark.django_db
def test_partial_layout_rejects_overlap_with_existing_widget(client):
    """Verify partial layout saves still validate omitted widgets."""
    owner = create_user(email="partial-layout-owner@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    first_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "First",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 1,
        },
    ).json()["data"]["id"]
    add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "Second",
            "config": {},
            "x": 4,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 2,
        },
    )

    response = json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/layout/",
        {"widgets": [{"id": first_widget_id, "x": 4, "y": 0, "w": 4, "h": 2, "order": 1}]},
        owner,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "layout"


@pytest.mark.integration
@pytest.mark.django_db
def test_widget_patch_rejects_overlap_with_existing_widget(client):
    """Verify direct widget edits cannot bypass layout collision checks."""
    owner = create_user(email="widget-patch-layout-owner@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    first_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "First",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 1,
        },
    ).json()["data"]["id"]
    add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "Second",
            "config": {},
            "x": 4,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 2,
        },
    )

    response = json_request(
        client,
        "patch",
        f"/api/v1/dashboards/{dashboard_id}/widgets/{first_widget_id}/",
        {"x": 3, "y": 0},
        owner,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "layout"


@pytest.mark.integration
@pytest.mark.django_db
def test_layout_allows_adjacent_widgets_and_persists_after_fetch(client):
    """Verify valid adjacent layouts can be saved and read back."""
    owner = create_user(email="adjacent-layout-owner@example.com")
    dashboard_id = create_dashboard_response(client, user=owner).json()["data"]["id"]
    first_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "First",
            "config": {},
            "x": 0,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 1,
        },
    ).json()["data"]["id"]
    second_widget_id = add_widget_response(
        client,
        user=owner,
        dashboard_id=dashboard_id,
        payload={
            "type": "metric_tile",
            "title": "Second",
            "config": {},
            "x": 4,
            "y": 0,
            "w": 4,
            "h": 2,
            "order": 2,
        },
    ).json()["data"]["id"]

    save_response = json_request(
        client,
        "put",
        f"/api/v1/dashboards/{dashboard_id}/layout/",
        {
            "widgets": [
                {"id": first_widget_id, "x": 0, "y": 2, "w": 4, "h": 2, "order": 1},
                {"id": second_widget_id, "x": 4, "y": 2, "w": 4, "h": 2, "order": 2},
            ]
        },
        owner,
    )
    fetch_response = client.get(f"/api/v1/dashboards/{dashboard_id}/", **auth_header(owner))
    widgets = {widget["id"]: widget for widget in fetch_response.json()["data"]["widgets"]}

    assert save_response.status_code == 200
    assert fetch_response.status_code == 200
    assert widgets[first_widget_id]["x"] == 0
    assert widgets[first_widget_id]["y"] == 2
    assert widgets[second_widget_id]["x"] == 4
    assert widgets[second_widget_id]["y"] == 2
