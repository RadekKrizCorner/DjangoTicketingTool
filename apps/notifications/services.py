"""Notification business services."""

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import EmailDelivery, Notification


def create_notification(
    *,
    user,
    type: str,
    title: str,
    message: str,
    dedupe_key: str,
    project=None,
    task=None,
) -> Notification:
    """Create a notification and matching pending email delivery."""
    with transaction.atomic():
        notification, _created = Notification.objects.get_or_create(
            user=user,
            dedupe_key=dedupe_key,
            defaults={
                "type": type,
                "title": title,
                "message": message,
                "project": project,
                "task": task,
            },
        )
        EmailDelivery.objects.get_or_create(
            notification=notification,
            user=user,
            defaults={"email": user.email, "subject": title, "body": message},
        )
        return notification


def mark_notification_read(*, notification: Notification) -> Notification:
    """Mark one notification as read."""
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
    return notification


def mark_all_notifications_read(*, user) -> int:
    """Mark all unread notifications for a user as read."""
    now = timezone.now()
    return Notification.objects.filter(
        user=user,
        read_at__isnull=True,
        deleted_at__isnull=True,
    ).update(read_at=now, updated_at=now)
