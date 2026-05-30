"""API URL routes for version 1."""

from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = [
    path("health/", include("apps.health.api.urls")),
]
