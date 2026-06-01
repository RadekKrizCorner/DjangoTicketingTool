"""Integration tests for task watcher behavior."""

import pytest

from apps.notifications.models import EmailDelivery, Notification
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task
from tests.factories import (
    add_project_member,
    auth_header,
    create_project,
    create_task,
    create_user,
    json_patch,
    json_post,
)


def task_url(project_id: int, task_id: int | None = None, suffix: str = "") -> str:
    """Return a project task URL."""
    if task_id is None:
        return f"/api/v1/projects/{project_id}/tasks/{suffix}"
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/{suffix}"


def comments_url(project_id: int, task_id: int) -> str:
    """Return a task comments URL."""
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/"


def comment_url(project_id: int, task_id: int, comment_id: int) -> str:
    """Return a task comment detail URL."""
    return f"/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/"


def task_watcher_model():
    """Return the task watcher model."""
    from django.apps import apps

    return apps.get_model("tasks", "TaskWatcher")


def active_watcher_user_ids(*, task_id: int) -> set[int]:
    """Return active watcher user IDs for a task."""
    TaskWatcher = task_watcher_model()
    return set(
        TaskWatcher.objects.filter(task_id=task_id, deleted_at__isnull=True).values_list(
            "user_id",
            flat=True,
        )
    )


def clear_notifications() -> None:
    """Delete existing notification and email delivery rows."""
    EmailDelivery.objects.all().delete()
    Notification.objects.all().delete()


@pytest.mark.integration
@pytest.mark.django_db
def test_task_create_auto_watches_creator_and_assignee_and_returns_watched(client):
    """Verify task creation subscribes creator and assignee."""
    owner = create_user()
    assignee = create_user()
    project = create_project(
        owner=owner,
        name="Watch create",
        visibility=Project.Visibility.PRIVATE,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )

    response = json_post(
        client,
        task_url(project.id),
        {"title": "Watched task", "assignee_id": assignee.id},
        owner,
    )
    task_id = response.json()["data"]["id"]
    assignee_detail = client.get(task_url(project.id, task_id), **auth_header(assignee))

    assert response.status_code == 201
    assert response.json()["data"]["watched"] is True
    assert assignee_detail.status_code == 200
    assert assignee_detail.json()["data"]["watched"] is True
    assert active_watcher_user_ids(task_id=task_id) == {owner.id, assignee.id}
    assert Notification.objects.filter(
        user=assignee,
        task_id=task_id,
        type="task_assigned",
    ).count() == 1
    assert EmailDelivery.objects.filter(notification__task_id=task_id).count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_project_member_can_watch_and_unwatch_their_own_subscription(client):
    """Verify an active project member can toggle their watcher state."""
    owner = create_user()
    member = create_user()
    assignee = create_user()
    project = create_project(
        owner=owner,
        name="Watch toggle",
        visibility=Project.Visibility.PUBLIC,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=member,
        role=ProjectMembership.Role.VIEWER,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)

    watch_response = json_post(client, task_url(project.id, task.id, "watch/"), {}, member)
    unwatch_response = client.delete(task_url(project.id, task.id, "watch/"), **auth_header(member))
    second_unwatch_response = client.delete(
        task_url(project.id, task.id, "watch/"),
        **auth_header(member),
    )
    rewatch_response = json_post(client, task_url(project.id, task.id, "watch/"), {}, member)

    assert watch_response.status_code == 200
    assert watch_response.json()["data"] == {"watched": True}
    assert unwatch_response.status_code == 200
    assert unwatch_response.json()["data"] == {"watched": False}
    assert second_unwatch_response.status_code == 200
    assert second_unwatch_response.json()["data"] == {"watched": False}
    assert rewatch_response.status_code == 200
    assert rewatch_response.json()["data"] == {"watched": True}
    assert member.id in active_watcher_user_ids(task_id=task.id)


@pytest.mark.integration
@pytest.mark.django_db
def test_public_outsider_cannot_watch_visible_task(client):
    """Verify public visibility does not grant watcher access."""
    owner = create_user()
    assignee = create_user()
    outsider = create_user()
    project = create_project(owner=owner, name="Public watch", visibility=Project.Visibility.PUBLIC)
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)

    response = json_post(client, task_url(project.id, task.id, "watch/"), {}, outsider)

    assert response.status_code == 403
    assert response.json()["errors"][0]["code"] == "permission_denied"
    assert outsider.id not in active_watcher_user_ids(task_id=task.id)


@pytest.mark.integration
@pytest.mark.django_db
def test_reassignment_adds_new_assignee_and_keeps_previous_assignee_watching(client):
    """Verify reassignment subscribes the new assignee without removing the old one."""
    owner = create_user()
    old_assignee = create_user()
    new_assignee = create_user()
    project = create_project(
        owner=owner,
        name="Reassign watch",
        visibility=Project.Visibility.PRIVATE,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=old_assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=new_assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    task = create_task(actor=owner, project=project, assignee=old_assignee)
    clear_notifications()

    response = json_patch(
        client,
        task_url(project.id, task.id),
        {"assignee_id": new_assignee.id},
        owner,
    )

    assert response.status_code == 200
    assert active_watcher_user_ids(task_id=task.id) == {
        owner.id,
        old_assignee.id,
        new_assignee.id,
    }
    new_assignee_notifications = Notification.objects.filter(
        user=new_assignee,
        task=task,
        type="task_assigned",
    )
    old_assignee_notifications = Notification.objects.filter(
        user=old_assignee,
        task=task,
        type="task_updated",
    )
    assert new_assignee_notifications.count() == 1
    assert old_assignee_notifications.count() == 1
    assert Notification.objects.filter(user=owner, task=task).count() == 0


@pytest.mark.integration
@pytest.mark.django_db
def test_watcher_notifications_cover_task_and_comment_change_types(client):
    """Verify watcher notifications use specific types and exclude the actor."""
    owner = create_user()
    assignee = create_user()
    watcher = create_user()
    project = create_project(owner=owner, name="Typed watch", visibility=Project.Visibility.PRIVATE)
    add_project_member(
        actor=owner,
        project=project,
        user=assignee,
        role=ProjectMembership.Role.MEMBER,
    )
    add_project_member(
        actor=owner,
        project=project,
        user=watcher,
        role=ProjectMembership.Role.VIEWER,
    )
    task = create_task(actor=owner, project=project, assignee=assignee)
    json_post(client, task_url(project.id, task.id, "watch/"), {}, watcher)
    clear_notifications()

    update_response = json_patch(client, task_url(project.id, task.id), {"title": "Edited"}, owner)
    transition_response = json_post(
        client,
        task_url(project.id, task.id, "transition/"),
        {"status": Task.Status.ACCEPTED},
        owner,
    )
    comment_response = json_post(
        client,
        comments_url(project.id, task.id),
        {"body": "Review note"},
        owner,
    )
    comment_id = comment_response.json()["data"]["id"]
    comment_update_response = json_patch(
        client,
        comment_url(project.id, task.id, comment_id),
        {"body": "Updated note"},
        owner,
    )
    comment_delete_response = client.delete(
        comment_url(project.id, task.id, comment_id),
        **auth_header(owner),
    )
    task_delete_response = client.delete(task_url(project.id, task.id), **auth_header(owner))

    watcher_types = set(
        Notification.objects.filter(user=watcher, task_id=task.id).values_list("type", flat=True)
    )
    assignee_types = set(
        Notification.objects.filter(user=assignee, task_id=task.id).values_list("type", flat=True)
    )

    assert update_response.status_code == 200
    assert transition_response.status_code == 200
    assert comment_response.status_code == 201
    assert comment_update_response.status_code == 200
    assert comment_delete_response.status_code == 204
    assert task_delete_response.status_code == 204
    assert watcher_types == {
        "task_updated",
        "task_transitioned",
        "task_comment_created",
        "task_comment_updated",
        "task_comment_deleted",
        "task_deleted",
    }
    assert assignee_types == watcher_types
    assert Notification.objects.filter(user=owner, task_id=task.id).count() == 0
    assert EmailDelivery.objects.filter(notification__task_id=task.id).count() == 12
