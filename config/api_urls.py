"""API URL routes for version 1."""

from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        "schema/",
        SpectacularAPIView.as_view(
            permission_classes=[AllowAny],
            renderer_classes=[OpenApiJsonRenderer],
        ),
        name="schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="redoc",
    ),
    path("health/", include("apps.health.api.urls")),
]
