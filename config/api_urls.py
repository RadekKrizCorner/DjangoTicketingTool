"""API URL routes for version 1."""

from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

import apps.accounts.api.urls as accounts_api_urls
import apps.attachments.api.urls as attachments_api_urls
import apps.health.api.urls as health_api_urls
import apps.projects.api.urls as projects_api_urls
import apps.tasks.api.direct_urls as tasks_direct_api_urls

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
    path("attachments/", include(attachments_api_urls)),
    path("health/", include(health_api_urls)),
    path("projects/", include(projects_api_urls)),
    path("tasks/", include(tasks_direct_api_urls)),
    path("users/", include(accounts_api_urls)),
]
