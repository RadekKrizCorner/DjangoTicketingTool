"""Direct task API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.tasks.api.views import DueSoonTasksView, MyTasksView

urlpatterns: list[URLPattern] = [
    path("my/", MyTasksView.as_view(), name="task-my"),
    path("due-soon/", DueSoonTasksView.as_view(), name="task-due-soon"),
]
