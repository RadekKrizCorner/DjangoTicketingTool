"""Health API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from .views import live_health

urlpatterns: list[URLPattern] = [
    path("live/", live_health, name="health-live"),
]
