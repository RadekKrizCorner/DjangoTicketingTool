"""Nested task API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.tasks.api.views import (
    TaskCommentDetailView,
    TaskCommentListCreateView,
    TaskDetailView,
    TaskListCreateView,
    TaskTransitionView,
    TaskWatchView,
)

urlpatterns: list[URLPattern] = [
    path("", TaskListCreateView.as_view(), name="project-task-list"),
    path("<int:task_id>/", TaskDetailView.as_view(), name="project-task-detail"),
    path(
        "<int:task_id>/transition/",
        TaskTransitionView.as_view(),
        name="project-task-transition",
    ),
    path(
        "<int:task_id>/watch/",
        TaskWatchView.as_view(),
        name="project-task-watch",
    ),
    path(
        "<int:task_id>/comments/",
        TaskCommentListCreateView.as_view(),
        name="project-task-comment-list",
    ),
    path(
        "<int:task_id>/comments/<int:comment_id>/",
        TaskCommentDetailView.as_view(),
        name="project-task-comment-detail",
    ),
]
