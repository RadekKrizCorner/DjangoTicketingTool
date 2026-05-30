"""Root URL configuration for the project."""

from django.contrib import admin
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]
