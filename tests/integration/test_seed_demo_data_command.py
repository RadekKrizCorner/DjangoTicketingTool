"""Integration tests for the demo data seed command."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from apps.attachments.models import Attachment
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskComment

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def run_seed_command(**options) -> str:
    """Run the seed command and return its stdout."""
    stdout = StringIO()
    call_command("seed_demo_data", stdout=stdout, **options)
    return stdout.getvalue()


def test_seed_demo_data_creates_idempotent_demo_dataset():
    """Verify the seed command creates one stable demo dataset."""
    options = {
        "users": 3,
        "projects": 2,
        "tasks_per_project": 2,
        "comments_per_task": 1,
        "seed": 15,
    }

    first_output = run_seed_command(**options)
    first_counts = {
        "users": get_user_model().objects.count(),
        "projects": Project.objects.count(),
        "memberships": ProjectMembership.objects.count(),
        "tasks": Task.objects.count(),
        "comments": TaskComment.objects.count(),
        "attachments": Attachment.objects.count(),
        "notifications": Notification.objects.count(),
        "demo_notifications": Notification.objects.filter(type="demo_welcome").count(),
    }
    second_output = run_seed_command(**options)
    second_counts = {
        "users": get_user_model().objects.count(),
        "projects": Project.objects.count(),
        "memberships": ProjectMembership.objects.count(),
        "tasks": Task.objects.count(),
        "comments": TaskComment.objects.count(),
        "attachments": Attachment.objects.count(),
        "notifications": Notification.objects.count(),
        "demo_notifications": Notification.objects.filter(type="demo_welcome").count(),
    }

    admin = get_user_model().objects.get(email="demo.admin@example.com")
    assert admin.is_superuser is True
    assert admin.is_staff is True
    assert admin.check_password("DemoAdmin123!") is True
    assert first_counts["notifications"] >= first_counts["demo_notifications"]
    assert {
        key: first_counts[key]
        for key in (
            "users",
            "projects",
            "memberships",
            "tasks",
            "comments",
            "attachments",
            "demo_notifications",
        )
    } == {
        "users": 4,
        "projects": 2,
        "memberships": 8,
        "tasks": 4,
        "comments": 4,
        "attachments": 4,
        "demo_notifications": 3,
    }
    assert second_counts == first_counts
    assert "Seeded demo data" in first_output
    assert "Seeded demo data" in second_output


def test_seed_demo_data_uses_superuser_environment(monkeypatch):
    """Verify predefined superuser values can be overridden by environment."""
    monkeypatch.setenv("DEMO_SUPERUSER_EMAIL", "teacher@example.com")
    monkeypatch.setenv("DEMO_SUPERUSER_PASSWORD", "TeacherDemo123!")
    monkeypatch.setenv("DEMO_SUPERUSER_DISPLAY_NAME", "Teacher Admin")

    run_seed_command(users=1, projects=1, tasks_per_project=1, comments_per_task=0, seed=3)

    admin = get_user_model().objects.get(email="teacher@example.com")
    assert admin.display_name == "Teacher Admin"
    assert admin.is_superuser is True
    assert admin.check_password("TeacherDemo123!") is True


@pytest.mark.kwparametrize(
    {
        "options": {"users": 0},
        "message": "users must be at least 1",
    },
    {
        "options": {"projects": 0},
        "message": "projects must be at least 1",
    },
    {
        "options": {"tasks_per_project": 0},
        "message": "tasks-per-project must be at least 1",
    },
    {
        "options": {"comments_per_task": -1},
        "message": "comments-per-task must be at least 0",
    },
)
def test_seed_demo_data_rejects_invalid_sizes(options, message):
    """Verify invalid dataset sizes are rejected before writing data."""
    with pytest.raises(CommandError, match=message):
        run_seed_command(**options)
