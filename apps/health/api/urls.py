"""Health API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.health.api.views import live_health, ready_health

urlpatterns: list[URLPattern] = [
    path("live/", live_health, name="health-live"),
    path("ready/", ready_health, name="health-ready"),
]
