"""Views for dashboard API endpoints."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.responses import success_response
from apps.dashboards import policies, renderers, selectors, services
from apps.dashboards.api.serializers import (
    DashboardCreateInputSerializer,
    DashboardLayoutInputSerializer,
    DashboardOutputSerializer,
    DashboardRenderInputSerializer,
    DashboardShareOutputSerializer,
    DashboardSharesInputSerializer,
    DashboardUpdateInputSerializer,
    DashboardWidgetInputSerializer,
    DashboardWidgetOutputSerializer,
    DashboardWidgetUpdateInputSerializer,
)


class DashboardListCreateView(APIView):
    """List and create dashboards."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        """Return dashboards visible to the current user."""
        dashboards = selectors.visible_dashboards_for_user(user=request.user)
        access_map = {
            dashboard.id: selectors.dashboard_access_for_user(
                dashboard=dashboard,
                user=request.user,
            )
            for dashboard in dashboards
        }
        return success_response(
            DashboardOutputSerializer(
                dashboards,
                many=True,
                context={"user": request.user, "access_map": access_map},
            ).data
        )

    def post(self, request: Request) -> Response:
        """Create a dashboard."""
        serializer = DashboardCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dashboard = services.create_dashboard(
            actor=request.user,
            name=serializer.validated_data["name"],
        )
        dashboard.effective_access = policies.ACCESS_OWNER
        return success_response(
            DashboardOutputSerializer(dashboard, context={"user": request.user}).data,
            status_code=status.HTTP_201_CREATED,
        )


class DashboardDetailView(APIView):
    """Read, update, and delete a dashboard."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, dashboard_id: int) -> Response:
        """Return one visible dashboard."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        return success_response(
            DashboardOutputSerializer(dashboard, context={"user": request.user}).data
        )

    def patch(self, request: Request, dashboard_id: int) -> Response:
        """Update one dashboard."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
            required_access=policies.ACCESS_EDITOR,
        )
        serializer = DashboardUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        dashboard = services.update_dashboard(
            actor=request.user,
            dashboard=dashboard,
            data=serializer.validated_data,
        )
        dashboard.effective_access = selectors.dashboard_access_for_user(
            dashboard=dashboard,
            user=request.user,
        )
        return success_response(
            DashboardOutputSerializer(dashboard, context={"user": request.user}).data
        )

    def delete(self, request: Request, dashboard_id: int) -> Response:
        """Soft delete one dashboard."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        services.soft_delete_dashboard(actor=request.user, dashboard=dashboard)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardWidgetListCreateView(APIView):
    """List and create dashboard widgets."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, dashboard_id: int) -> Response:
        """Return widgets for a dashboard."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        widgets = selectors.widgets_for_dashboard(dashboard=dashboard)
        return success_response(DashboardWidgetOutputSerializer(widgets, many=True).data)

    def post(self, request: Request, dashboard_id: int) -> Response:
        """Create a dashboard widget."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
            required_access=policies.ACCESS_EDITOR,
        )
        serializer = DashboardWidgetInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        widget = services.create_widget(
            actor=request.user,
            dashboard=dashboard,
            data=serializer.validated_data,
        )
        return success_response(
            DashboardWidgetOutputSerializer(widget).data,
            status_code=status.HTTP_201_CREATED,
        )


class DashboardWidgetDetailView(APIView):
    """Update and delete dashboard widgets."""

    permission_classes = (IsAuthenticated,)

    def patch(self, request: Request, dashboard_id: int, widget_id: int) -> Response:
        """Update one dashboard widget."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
            required_access=policies.ACCESS_EDITOR,
        )
        widget = selectors.widget_for_dashboard_or_404(dashboard=dashboard, widget_id=widget_id)
        serializer = DashboardWidgetUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        widget = services.update_widget(
            actor=request.user,
            widget=widget,
            data=serializer.validated_data,
        )
        return success_response(DashboardWidgetOutputSerializer(widget).data)

    def delete(self, request: Request, dashboard_id: int, widget_id: int) -> Response:
        """Soft delete one dashboard widget."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
            required_access=policies.ACCESS_EDITOR,
        )
        widget = selectors.widget_for_dashboard_or_404(dashboard=dashboard, widget_id=widget_id)
        services.soft_delete_widget(actor=request.user, widget=widget)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardLayoutView(APIView):
    """Update dashboard widget layout."""

    permission_classes = (IsAuthenticated,)

    def put(self, request: Request, dashboard_id: int) -> Response:
        """Save dashboard widget layout."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
            required_access=policies.ACCESS_EDITOR,
        )
        serializer = DashboardLayoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        widgets = services.update_layout(
            actor=request.user,
            dashboard=dashboard,
            widgets=serializer.validated_data["widgets"],
        )
        return success_response(
            {"widgets": DashboardWidgetOutputSerializer(widgets, many=True).data}
        )


class DashboardSharesView(APIView):
    """Read and replace dashboard shares."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, dashboard_id: int) -> Response:
        """Return dashboard shares."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        if not policies.can_manage_dashboard_shares(actor=request.user, dashboard=dashboard):
            selectors.raise_permission_denied()
        return success_response(
            DashboardShareOutputSerializer(
                selectors.shares_for_dashboard(dashboard=dashboard),
                many=True,
            ).data
        )

    def put(self, request: Request, dashboard_id: int) -> Response:
        """Replace dashboard shares."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        serializer = DashboardSharesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shares = services.replace_shares(
            actor=request.user,
            dashboard=dashboard,
            shares=serializer.validated_data["shares"],
        )
        return success_response(DashboardShareOutputSerializer(shares, many=True).data)


class DashboardRenderView(APIView):
    """Render dashboard widget data."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, dashboard_id: int) -> Response:
        """Return rendered widget data for a dashboard."""
        dashboard = selectors.dashboard_for_user_or_404(
            user=request.user,
            dashboard_id=dashboard_id,
        )
        serializer = DashboardRenderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(
            renderers.render_dashboard(
                dashboard=dashboard,
                user=request.user,
                filters=serializer.validated_data["filters"],
            )
        )
