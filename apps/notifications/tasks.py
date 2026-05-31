"""Celery tasks for notification and scheduled project work."""

from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit_log
from apps.notifications.models import EmailDelivery, Notification
from apps.notifications.services import create_notification
from apps.projects.models import Project, ProjectMembership
from apps.projects.services import project_snapshot
from apps.tasks.models import Task


@shared_task
def publish_due_projects() -> int:
    """Publish due projects and notify active members once."""
    now = timezone.now()
    changed = 0
    due_projects = Project.objects.filter(
        deleted_at__isnull=True,
        visibility=Project.Visibility.PRIVATE,
        publish_at__isnull=False,
        publish_at__lte=now,
        published_at__isnull=True,
    ).order_by("publish_at", "id")
    for project in due_projects:
        with transaction.atomic():
            locked_project = Project.objects.select_for_update().get(pk=project.pk)
            if not project_is_publish_due(project=locked_project, now=now):
                continue
            before = project_snapshot(locked_project)
            locked_project.visibility = Project.Visibility.PUBLIC
            locked_project.published_at = now
            locked_project.publish_at = None
            locked_project.save(
                update_fields=["visibility", "published_at", "publish_at", "updated_at"]
            )
            record_audit_log(
                action="project.published",
                entity_type="project",
                entity_id=locked_project.id,
                project=locked_project,
                before=before,
                after=project_snapshot(locked_project),
                idempotency_key=f"project:{locked_project.id}:published",
            )
            notify_project_members(
                project=locked_project,
                type="project_published",
                title=f"Project published: {locked_project.name}",
                message=f"Project {locked_project.name} is now public.",
                key_suffix="published",
            )
            changed += 1
    return changed


@shared_task
def close_due_projects() -> int:
    """Close due projects and notify active members once."""
    now = timezone.now()
    changed = 0
    due_projects = Project.objects.filter(
        deleted_at__isnull=True,
        state=Project.State.ACTIVE,
        close_at__isnull=False,
        close_at__lte=now,
    ).order_by("close_at", "id")
    for project in due_projects:
        with transaction.atomic():
            locked_project = Project.objects.select_for_update().get(pk=project.pk)
            if not project_is_close_due(project=locked_project, now=now):
                continue
            before = project_snapshot(locked_project)
            locked_project.state = Project.State.CLOSED
            locked_project.closed_at = now
            locked_project.close_at = None
            locked_project.save(update_fields=["state", "closed_at", "close_at", "updated_at"])
            record_audit_log(
                action="project.closed",
                entity_type="project",
                entity_id=locked_project.id,
                project=locked_project,
                before=before,
                after=project_snapshot(locked_project),
                idempotency_key=f"project:{locked_project.id}:closed",
            )
            notify_project_members(
                project=locked_project,
                type="project_closed",
                title=f"Project closed: {locked_project.name}",
                message=f"Project {locked_project.name} has been closed.",
                key_suffix="closed",
            )
            changed += 1
    return changed


@shared_task
def send_deadline_reminders() -> int:
    """Create deadline reminder notifications for tasks due soon."""
    now = timezone.now()
    due_until = now + timedelta(hours=24)
    created = 0
    tasks = (
        Task.objects.filter(
            deleted_at__isnull=True,
            project__deleted_at__isnull=True,
            project__state=Project.State.ACTIVE,
            due_at__isnull=False,
            due_at__gte=now,
            due_at__lte=due_until,
        )
        .exclude(status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED])
        .select_related("assignee", "project")
        .order_by("due_at", "id")
    )
    for task in tasks:
        dedupe_key = f"task:{task.id}:deadline:{task.due_at.isoformat()}"
        if Notification.objects.filter(user=task.assignee, dedupe_key=dedupe_key).exists():
            continue
        create_notification(
            user=task.assignee,
            type="task_deadline_reminder",
            title=f"Task due soon: {task.title}",
            message=f"Task {task.title} is due at {task.due_at.isoformat()}.",
            dedupe_key=dedupe_key,
            project=task.project,
            task=task,
        )
        created += 1
    return created


@shared_task
def send_pending_emails() -> int:
    """Send pending email delivery rows."""
    attempted = 0
    deliveries = EmailDelivery.objects.filter(status=EmailDelivery.Status.PENDING).order_by(
        "created_at",
        "id",
    )
    for delivery in deliveries:
        with transaction.atomic():
            locked_delivery = EmailDelivery.objects.select_for_update().get(pk=delivery.pk)
            if locked_delivery.status != EmailDelivery.Status.PENDING:
                continue
            attempted += 1
            try:
                send_mail(
                    subject=locked_delivery.subject,
                    message=locked_delivery.body,
                    from_email=None,
                    recipient_list=[locked_delivery.email],
                    fail_silently=False,
                )
            except Exception as exc:
                locked_delivery.status = EmailDelivery.Status.FAILED
                locked_delivery.error_message = str(exc)
                locked_delivery.save(update_fields=["status", "error_message"])
            else:
                locked_delivery.status = EmailDelivery.Status.SENT
                locked_delivery.sent_at = timezone.now()
                locked_delivery.save(update_fields=["status", "sent_at"])
    return attempted


def project_is_publish_due(*, project: Project, now) -> bool:
    """Return whether a locked project should be published."""
    return bool(
        project.visibility == Project.Visibility.PRIVATE
        and project.publish_at is not None
        and project.publish_at <= now
        and project.published_at is None
    )


def project_is_close_due(*, project: Project, now) -> bool:
    """Return whether a locked project should be closed."""
    return bool(
        project.state == Project.State.ACTIVE
        and project.close_at is not None
        and project.close_at <= now
    )


def notify_project_members(
    *,
    project: Project,
    type: str,
    title: str,
    message: str,
    key_suffix: str,
) -> None:
    """Create notifications for all active project members."""
    memberships = ProjectMembership.objects.filter(
        project=project,
        deleted_at__isnull=True,
    ).select_related("user")
    for membership in memberships:
        create_notification(
            user=membership.user,
            type=type,
            title=title,
            message=message,
            dedupe_key=f"project:{project.id}:{key_suffix}:user:{membership.user_id}",
            project=project,
        )
