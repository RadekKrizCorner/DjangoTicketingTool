"""Seed a deterministic demo dataset for local and release environments."""

import os
import random
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.attachments.models import Attachment
from apps.attachments.services import create_attachment
from apps.notifications.services import create_notification
from apps.projects.models import Project, ProjectMembership
from apps.projects.services import add_project_member, create_project
from apps.tasks.models import Task, TaskComment
from apps.tasks.services import create_comment, create_task, transition_task

DEFAULT_SUPERUSER_EMAIL = "demo.admin@example.com"
DEFAULT_SUPERUSER_PASSWORD = "DemoAdmin123!"
DEFAULT_SUPERUSER_DISPLAY_NAME = "Demo Admin"
DEFAULT_DEMO_USER_PASSWORD = "DemoUser123!"

PROJECT_DOMAINS = [
    "Customer Portal",
    "Operations Dashboard",
    "Mobile API",
    "Billing Automation",
    "Audit Console",
]
TASK_VERBS = ["Design", "Implement", "Review", "Harden", "Document", "Validate"]
TASK_OBJECTS = [
    "JWT login flow",
    "project permissions",
    "deadline reminders",
    "attachment quotas",
    "audit export",
    "release checklist",
]
COMMENT_TEMPLATES = [
    "Checked the current behavior and left notes for the next iteration.",
    "Added acceptance criteria so the frontend can use the endpoint safely.",
    "Validated the edge cases against the product specification.",
]
TASK_STATUS_PATHS = {
    Task.Status.NEW: [],
    Task.Status.ACCEPTED: [Task.Status.ACCEPTED],
    Task.Status.IN_PROGRESS: [Task.Status.ACCEPTED, Task.Status.IN_PROGRESS],
    Task.Status.ON_HOLD: [Task.Status.ACCEPTED, Task.Status.ON_HOLD],
    Task.Status.COMPLETED: [Task.Status.ACCEPTED, Task.Status.IN_PROGRESS, Task.Status.COMPLETED],
    Task.Status.CANCELLED: [Task.Status.CANCELLED],
}


@dataclass(frozen=True)
class SeedOptions:
    """Store normalized demo seed options."""

    users: int
    projects: int
    tasks_per_project: int
    comments_per_task: int
    seed: int
    superuser_email: str
    superuser_password: str
    superuser_display_name: str
    demo_user_password: str


class Command(BaseCommand):
    """Create or update deterministic demo users, projects, tasks, and comments."""

    help = "Create a deterministic demo dataset for local review."

    def add_arguments(self, parser: CommandParser) -> None:
        """Register command line arguments."""
        parser.add_argument("--users", type=int, default=5)
        parser.add_argument("--projects", type=int, default=3)
        parser.add_argument("--tasks-per-project", type=int, default=5)
        parser.add_argument("--comments-per-task", type=int, default=2)
        parser.add_argument("--seed", type=int, default=20260601)

    def handle(self, *args: Any, **options: Any) -> None:
        """Create demo data and print a summary."""
        seed_options = build_seed_options(options)
        randomizer = random.Random(seed_options.seed)

        with transaction.atomic():
            superuser = ensure_superuser(options=seed_options)
            users = ensure_demo_users(options=seed_options)
            projects = ensure_projects(
                actor=superuser,
                users=users,
                options=seed_options,
                randomizer=randomizer,
            )
            tasks = ensure_tasks(
                actor=superuser,
                projects=projects,
                users=users,
                options=seed_options,
                randomizer=randomizer,
            )
            ensure_comments_and_attachments(
                users=users,
                tasks=tasks,
                options=seed_options,
                randomizer=randomizer,
            )
            ensure_notifications(users=users)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo data: "
                f"superuser={seed_options.superuser_email}, "
                f"users={len(users)}, projects={len(projects)}, tasks={len(tasks)}"
            )
        )


def build_seed_options(options: dict[str, Any]) -> SeedOptions:
    """Return validated seed options from CLI and environment values."""
    users = int(options["users"])
    projects = int(options["projects"])
    tasks_per_project = int(options["tasks_per_project"])
    comments_per_task = int(options["comments_per_task"])
    if users < 1:
        raise CommandError("users must be at least 1")
    if projects < 1:
        raise CommandError("projects must be at least 1")
    if tasks_per_project < 1:
        raise CommandError("tasks-per-project must be at least 1")
    if comments_per_task < 0:
        raise CommandError("comments-per-task must be at least 0")

    return SeedOptions(
        users=users,
        projects=projects,
        tasks_per_project=tasks_per_project,
        comments_per_task=comments_per_task,
        seed=int(options["seed"]),
        superuser_email=os.getenv("DEMO_SUPERUSER_EMAIL", DEFAULT_SUPERUSER_EMAIL),
        superuser_password=os.getenv("DEMO_SUPERUSER_PASSWORD", DEFAULT_SUPERUSER_PASSWORD),
        superuser_display_name=os.getenv(
            "DEMO_SUPERUSER_DISPLAY_NAME",
            DEFAULT_SUPERUSER_DISPLAY_NAME,
        ),
        demo_user_password=os.getenv("DEMO_USER_PASSWORD", DEFAULT_DEMO_USER_PASSWORD),
    )


def ensure_superuser(*, options: SeedOptions):
    """Create or update the predefined demo superuser."""
    user_model = get_user_model()
    email = user_model.objects.normalize_email(options.superuser_email)
    user, _created = user_model.objects.get_or_create(
        email=email,
        defaults={
            "display_name": options.superuser_display_name,
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    user.display_name = options.superuser_display_name
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.set_password(options.superuser_password)
    user.save(update_fields=["display_name", "is_active", "is_staff", "is_superuser", "password"])
    return user


def ensure_demo_users(*, options: SeedOptions) -> list:
    """Create or update deterministic non-staff demo users."""
    user_model = get_user_model()
    users = []
    for index in range(1, options.users + 1):
        email = f"demo.user{index:02d}@example.com"
        user, _created = user_model.objects.get_or_create(
            email=email,
            defaults={
                "display_name": f"Demo User {index:02d}",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        user.display_name = f"Demo User {index:02d}"
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(options.demo_user_password)
        user.save(
            update_fields=["display_name", "is_active", "is_staff", "is_superuser", "password"]
        )
        users.append(user)
    return users


def ensure_projects(
    *,
    actor,
    users: list,
    options: SeedOptions,
    randomizer: random.Random,
) -> list[Project]:
    """Create deterministic projects and memberships."""
    projects = []
    roles = [
        ProjectMembership.Role.MANAGER,
        ProjectMembership.Role.MEMBER,
        ProjectMembership.Role.VIEWER,
    ]
    for index in range(1, options.projects + 1):
        domain = PROJECT_DOMAINS[(index - 1) % len(PROJECT_DOMAINS)]
        name = f"Demo Project {index:02d} - {domain}"
        project = active_project_by_name(name=name)
        if project is None:
            project = create_project(
                actor=actor,
                data={
                    "name": name,
                    "description": f"Demo project for {domain.lower()} review workflows.",
                    "visibility": project_visibility(index=index),
                    "public_comment_policy": project_comment_policy(index=index),
                },
            )
        projects.append(project)
        for user_index, user in enumerate(users):
            role = roles[(user_index + randomizer.randrange(len(roles))) % len(roles)]
            ensure_project_membership(actor=actor, project=project, user=user, role=role)
    return projects


def ensure_tasks(
    *,
    actor,
    projects: list[Project],
    users: list,
    options: SeedOptions,
    randomizer: random.Random,
) -> list[Task]:
    """Create deterministic tasks for every demo project."""
    tasks = []
    statuses = list(TASK_STATUS_PATHS)
    priorities = list(Task.Priority.values)
    now = timezone.now()
    for project_index, project in enumerate(projects, start=1):
        for task_index in range(1, options.tasks_per_project + 1):
            title = demo_task_title(
                project_index=project_index,
                task_index=task_index,
                randomizer=randomizer,
            )
            due_at = now + timedelta(days=randomizer.randint(1, 14))
            assignee = users[(project_index + task_index - 2) % len(users)]
            task = active_task_by_title(project=project, title=title)
            if task is None:
                task = create_task(
                    actor=actor,
                    project=project,
                    data={
                        "title": title,
                        "description": "Generated demo task with workflow and audit history.",
                        "assignee": assignee,
                        "priority": priorities[(project_index + task_index) % len(priorities)],
                        "due_at": due_at,
                    },
                )
                target_status = statuses[(project_index + task_index) % len(statuses)]
                move_task_to_status(actor=actor, task=task, target_status=target_status)
            tasks.append(task)
    return tasks


def ensure_comments_and_attachments(
    *,
    users: list,
    tasks: list[Task],
    options: SeedOptions,
    randomizer: random.Random,
) -> None:
    """Create deterministic comments and one text attachment per task."""
    for task_index, task in enumerate(tasks, start=1):
        for comment_index in range(1, options.comments_per_task + 1):
            author = users[(task_index + comment_index - 2) % len(users)]
            body = (
                f"Demo comment {comment_index:02d} for task {task_index:02d}. "
                f"{randomizer.choice(COMMENT_TEMPLATES)}"
            )
            ensure_comment(task=task, author=author, body=body)
        ensure_task_attachment(task=task, actor=task.project.owner, task_index=task_index)


def ensure_notifications(*, users: list) -> None:
    """Create deterministic welcome notifications for demo users."""
    for user in users:
        create_notification(
            user=user,
            type="demo_welcome",
            title="Demo workspace ready",
            message="Your demo account has seeded projects, tasks, comments, and notifications.",
            dedupe_key=f"demo:user:{user.email}:welcome",
        )


def active_project_by_name(*, name: str) -> Project | None:
    """Return the active project with a matching demo name."""
    return Project.objects.filter(name=name, deleted_at__isnull=True).first()


def active_task_by_title(*, project: Project, title: str) -> Task | None:
    """Return the active task with a matching demo title."""
    return Task.objects.filter(project=project, title=title, deleted_at__isnull=True).first()


def project_visibility(*, index: int) -> str:
    """Return a deterministic project visibility for an index."""
    if index % 2 == 0:
        return Project.Visibility.PUBLIC
    return Project.Visibility.PRIVATE


def project_comment_policy(*, index: int) -> str:
    """Return a deterministic public comment policy for an index."""
    if index % 2 == 0:
        return Project.PublicCommentPolicy.AUTHENTICATED_USERS
    return Project.PublicCommentPolicy.MEMBERS_ONLY


def ensure_project_membership(*, actor, project: Project, user, role: str) -> ProjectMembership:
    """Create or return an active project membership."""
    membership = ProjectMembership.objects.filter(
        project=project,
        user=user,
        deleted_at__isnull=True,
    ).first()
    if membership is not None:
        return membership
    return add_project_member(actor=actor, project=project, user=user, role=role)


def demo_task_title(
    *,
    project_index: int,
    task_index: int,
    randomizer: random.Random,
) -> str:
    """Return a deterministic demo task title."""
    verb = randomizer.choice(TASK_VERBS)
    target = randomizer.choice(TASK_OBJECTS)
    return f"Demo P{project_index:02d} T{task_index:02d} - {verb} {target}"


def move_task_to_status(*, actor, task: Task, target_status: str) -> Task:
    """Move a new task through the allowed workflow path."""
    current_task = task
    for status in TASK_STATUS_PATHS[target_status]:
        if current_task.status == status:
            continue
        current_task = transition_task(
            actor=actor,
            task=current_task,
            target_status=status,
            note="Demo seed workflow transition.",
        )
    return current_task


def ensure_comment(*, task: Task, author, body: str) -> TaskComment:
    """Create or return a deterministic task comment."""
    comment = TaskComment.objects.filter(
        task=task,
        author=author,
        body=body,
        deleted_at__isnull=True,
    ).first()
    if comment is not None:
        return comment
    return create_comment(actor=author, task=task, body=body)


def ensure_task_attachment(*, task: Task, actor, task_index: int) -> Attachment:
    """Create or return a deterministic text attachment for a task."""
    filename = f"demo-task-{task_index:02d}.log"
    attachment = Attachment.objects.filter(
        task=task,
        original_filename=filename,
        deleted_at__isnull=True,
    ).first()
    if attachment is not None:
        return attachment
    uploaded_file = SimpleUploadedFile(
        filename,
        f"Demo log for task {task.id}: {task.title}\n".encode(),
        content_type="text/plain",
    )
    return create_attachment(actor=actor, parent=task, uploaded_file=uploaded_file)
