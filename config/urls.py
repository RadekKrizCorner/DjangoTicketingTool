"""Root URL configuration for the project."""

from django.contrib import admin
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

from apps.common.views import docs_page, home_page, ui_page
from apps.observability.views import metrics_view

urlpatterns: list[URLPattern | URLResolver] = [
    path("", home_page, name="home"),
    path("ui/", ui_page, name="ui"),
    path("docs/", docs_page, name="docs"),
    path("internal/metrics/", metrics_view, name="observability-metrics"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]
