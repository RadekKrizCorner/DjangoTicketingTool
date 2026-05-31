"""Attachment API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.attachments.api.views import AttachmentDetailView, AttachmentDownloadView

urlpatterns: list[URLPattern] = [
    path(
        "<int:attachment_id>/download/",
        AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
    path("<int:attachment_id>/", AttachmentDetailView.as_view(), name="attachment-detail"),
]
