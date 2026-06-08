"""Dashboard API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.dashboards.api.views import (
    DashboardDetailView,
    DashboardLayoutView,
    DashboardListCreateView,
    DashboardRenderView,
    DashboardSharesView,
    DashboardWidgetDetailView,
    DashboardWidgetListCreateView,
)

urlpatterns: list[URLPattern] = [
    path("", DashboardListCreateView.as_view(), name="dashboard-list"),
    path("<int:dashboard_id>/", DashboardDetailView.as_view(), name="dashboard-detail"),
    path(
        "<int:dashboard_id>/widgets/",
        DashboardWidgetListCreateView.as_view(),
        name="dashboard-widget-list",
    ),
    path(
        "<int:dashboard_id>/widgets/<int:widget_id>/",
        DashboardWidgetDetailView.as_view(),
        name="dashboard-widget-detail",
    ),
    path(
        "<int:dashboard_id>/layout/",
        DashboardLayoutView.as_view(),
        name="dashboard-layout",
    ),
    path(
        "<int:dashboard_id>/shares/",
        DashboardSharesView.as_view(),
        name="dashboard-shares",
    ),
    path(
        "<int:dashboard_id>/render/",
        DashboardRenderView.as_view(),
        name="dashboard-render",
    ),
]
