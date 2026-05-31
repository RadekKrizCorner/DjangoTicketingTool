"""Notification query selectors."""

from http import HTTPStatus

from django.db.models import QuerySet

from apps.common.errors import DomainError
from apps.notifications.models import Notification


def notifications_for_user(*, user) -> QuerySet[Notification]:
    """Return non-deleted notifications for a user."""
    return Notification.objects.filter(user=user, deleted_at__isnull=True).order_by(
        "-created_at",
        "-id",
    )


def notification_for_user_or_404(*, user, notification_id: int) -> Notification:
    """Return a user-owned notification or raise not found."""
    notification = notifications_for_user(user=user).filter(pk=notification_id).first()
    if notification is None:
        raise DomainError(
            code="not_found",
            detail="Notification was not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )
    return notification
