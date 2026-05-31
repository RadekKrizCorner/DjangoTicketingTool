"""Notification API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.notifications.api.views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
)

urlpatterns: list[URLPattern] = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<int:notification_id>/read/", NotificationReadView.as_view(), name="notification-read"),
]
