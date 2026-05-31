"""Integration tests for scheduled notification jobs."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.projects.models import Project
from apps.tasks.models import Task
from tests.integration.projects.test_project_api import add_member, create_project, create_user
from tests.integration.tasks.test_task_api import create_task


@pytest.mark.integration
@pytest.mark.django_db
def test_publish_due_projects_is_idempotent(client):
    """Verify publishing due projects twice creates one notification set."""
    from apps.notifications.models import EmailDelivery, Notification
    from apps.notifications.tasks import publish_due_projects

    owner = create_user("notify-publish-owner@example.com")
    member = create_user("notify-publish-member@example.com")
    project_data = create_project(client, owner, name="Publish Due", visibility="private")
    add_member(client, owner, project_data["id"], member, role="member")
    Project.objects.filter(pk=project_data["id"]).update(publish_at=timezone.now())
    project = Project.objects.get(pk=project_data["id"])

    first_count = publish_due_projects()
    second_count = publish_due_projects()
    project.refresh_from_db()

    assert first_count == 1
    assert second_count == 0
    assert project.visibility == "public"
    assert project.published_at is not None
    assert project.publish_at is None
    assert Notification.objects.filter(project=project, type="project_published").count() == 2
    assert EmailDelivery.objects.filter(notification__project=project).count() == 2


@pytest.mark.integration
@pytest.mark.django_db
def test_close_due_projects_is_idempotent(client):
    """Verify closing due projects twice changes the project once."""
    from apps.notifications.models import Notification
    from apps.notifications.tasks import close_due_projects

    owner = create_user("notify-close-owner@example.com")
    project_data = create_project(client, owner, name="Close Due", visibility="private")
    Project.objects.filter(pk=project_data["id"]).update(close_at=timezone.now())
    project = Project.objects.get(pk=project_data["id"])

    first_count = close_due_projects()
    second_count = close_due_projects()
    project.refresh_from_db()

    assert first_count == 1
    assert second_count == 0
    assert project.state == "closed"
    assert project.closed_at is not None
    assert project.close_at is None
    assert Notification.objects.filter(project=project, type="project_closed").count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_deadline_reminders_are_deduplicated(client):
    """Verify deadline reminders are sent at most once per task deadline."""
    from apps.notifications.models import Notification
    from apps.notifications.tasks import send_deadline_reminders

    owner = create_user("notify-deadline-owner@example.com")
    assignee = create_user("notify-deadline-assignee@example.com")
    project_data = create_project(client, owner, name="Deadline Due", visibility="private")
    add_member(client, owner, project_data["id"], assignee, role="member")
    task_data = create_task(client, owner, project_data["id"], assignee)
    due_at = timezone.now() + timedelta(hours=4)
    Task.objects.filter(pk=task_data["id"]).update(due_at=due_at)
    task = Task.objects.get(pk=task_data["id"])

    first_count = send_deadline_reminders()
    second_count = send_deadline_reminders()

    assert first_count == 1
    assert second_count == 0
    assert Notification.objects.filter(task=task, type="task_deadline_reminder").count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_send_pending_emails_marks_deliveries_sent():
    """Verify pending email deliveries are sent once."""
    from apps.notifications.models import EmailDelivery
    from apps.notifications.services import create_notification
    from apps.notifications.tasks import send_pending_emails

    user = create_user("notify-email@example.com")
    create_notification(
        user=user,
        type="manual",
        title="Manual notification",
        message="Body",
        dedupe_key="manual:test",
    )

    attempted = send_pending_emails()
    second_attempt = send_pending_emails()
    delivery = EmailDelivery.objects.get(user=user)

    assert attempted == 1
    assert second_attempt == 0
    assert delivery.status == "sent"
    assert delivery.sent_at is not None
    assert len(mail.outbox) == 1
