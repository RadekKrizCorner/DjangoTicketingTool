"""Views for notification API endpoints."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import StandardPageNumberPagination
from apps.api.responses import success_response
from apps.notifications import selectors, services
from apps.notifications.api.serializers import NotificationOutputSerializer


class NotificationListView(APIView):
    """List user notifications."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        """Return notifications for the authenticated user."""
        notifications = selectors.notifications_for_user(user=request.user)
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(notifications, request, view=self)
        serializer = NotificationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class NotificationReadView(APIView):
    """Mark one notification read."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, notification_id: int) -> Response:
        """Mark one notification read."""
        notification = selectors.notification_for_user_or_404(
            user=request.user,
            notification_id=notification_id,
        )
        updated_notification = services.mark_notification_read(notification=notification)
        return success_response(NotificationOutputSerializer(updated_notification).data)


class NotificationReadAllView(APIView):
    """Mark all notifications read."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """Mark all notifications for the user read."""
        count = services.mark_all_notifications_read(user=request.user)
        return success_response({"status": "read", "count": count})
