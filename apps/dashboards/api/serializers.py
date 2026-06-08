"""Serializers for dashboard API endpoints."""

from rest_framework import serializers

from apps.accounts.api.serializers import UserSummarySerializer
from apps.dashboards import policies, validators
from apps.dashboards.models import Dashboard, DashboardShare, DashboardWidget


class DashboardWidgetOutputSerializer(serializers.Serializer):
    """Serialize dashboard widget output."""

    id = serializers.IntegerField()
    dashboard_id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=DashboardWidget.Type.choices)
    title = serializers.CharField()
    config = serializers.DictField()
    x = serializers.IntegerField()
    y = serializers.IntegerField()
    w = serializers.IntegerField()
    h = serializers.IntegerField()
    order = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class DashboardShareOutputSerializer(serializers.Serializer):
    """Serialize dashboard share output."""

    id = serializers.IntegerField()
    dashboard_id = serializers.IntegerField()
    target_type = serializers.ChoiceField(choices=DashboardShare.TargetType.choices)
    user_id = serializers.IntegerField(allow_null=True)
    user = UserSummarySerializer(allow_null=True)
    project_id = serializers.IntegerField(allow_null=True)
    project = serializers.SerializerMethodField()
    access = serializers.ChoiceField(choices=DashboardShare.Access.choices)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_project(self, obj: DashboardShare) -> dict | None:
        """Return a small project summary."""
        if obj.project is None:
            return None
        return {"id": obj.project_id, "name": obj.project.name}


class DashboardOutputSerializer(serializers.Serializer):
    """Serialize dashboard output."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    owner_id = serializers.IntegerField()
    owner = UserSummarySerializer()
    access = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    widgets = serializers.SerializerMethodField()
    shares = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_access(self, obj: Dashboard) -> str:
        """Return the current user's dashboard access."""
        return self._access(obj)

    def get_capabilities(self, obj: Dashboard) -> dict[str, bool]:
        """Return dashboard capabilities for the current user."""
        return policies.dashboard_capabilities(
            actor=self.context.get("user"),
            dashboard=obj,
            access=self._access(obj),
        )

    def get_widgets(self, obj: Dashboard) -> list[dict]:
        """Return dashboard widgets."""
        return DashboardWidgetOutputSerializer(
            obj.widgets.filter(deleted_at__isnull=True).order_by("order", "id"),
            many=True,
        ).data

    def get_shares(self, obj: Dashboard) -> list[dict]:
        """Return dashboard shares when requested in context."""
        if not self.context.get("include_shares", False):
            return []
        return DashboardShareOutputSerializer(
            obj.shares.filter(deleted_at__isnull=True).order_by("target_type", "id"),
            many=True,
        ).data

    def _access(self, obj: Dashboard) -> str:
        """Return cached dashboard access."""
        access_map = self.context.get("access_map")
        if access_map is not None and obj.id in access_map:
            return access_map[obj.id]
        return getattr(obj, "effective_access", policies.ACCESS_NONE)


class DashboardEnvelopeSerializer(serializers.Serializer):
    """Serialize a dashboard data envelope."""

    data = DashboardOutputSerializer()


class DashboardListEnvelopeSerializer(serializers.Serializer):
    """Serialize a dashboard list envelope."""

    data = DashboardOutputSerializer(many=True)


class DashboardCreateInputSerializer(serializers.Serializer):
    """Validate dashboard creation input."""

    name = serializers.CharField(max_length=200)


class DashboardUpdateInputSerializer(serializers.Serializer):
    """Validate dashboard update input."""

    name = serializers.CharField(max_length=200, required=False)


class DashboardWidgetInputSerializer(serializers.Serializer):
    """Validate dashboard widget input."""

    type = serializers.ChoiceField(choices=DashboardWidget.Type.choices)
    title = serializers.CharField(max_length=200)
    config = serializers.DictField(required=False, default=dict)
    x = serializers.IntegerField(min_value=0, required=False, default=0)
    y = serializers.IntegerField(min_value=0, required=False, default=0)
    w = serializers.IntegerField(min_value=1, required=False, default=3)
    h = serializers.IntegerField(min_value=1, required=False, default=2)
    order = serializers.IntegerField(min_value=1, required=False, default=1)


class DashboardWidgetUpdateInputSerializer(serializers.Serializer):
    """Validate dashboard widget update input."""

    type = serializers.ChoiceField(choices=DashboardWidget.Type.choices, required=False)
    title = serializers.CharField(max_length=200, required=False)
    config = serializers.DictField(required=False)
    x = serializers.IntegerField(min_value=0, required=False)
    y = serializers.IntegerField(min_value=0, required=False)
    w = serializers.IntegerField(min_value=1, required=False)
    h = serializers.IntegerField(min_value=1, required=False)
    order = serializers.IntegerField(min_value=1, required=False)


class DashboardLayoutWidgetInputSerializer(serializers.Serializer):
    """Validate one dashboard layout item."""

    id = serializers.IntegerField()
    x = serializers.IntegerField(min_value=0)
    y = serializers.IntegerField(min_value=0)
    w = serializers.IntegerField(min_value=1)
    h = serializers.IntegerField(min_value=1)
    order = serializers.IntegerField(min_value=1)


class DashboardLayoutInputSerializer(serializers.Serializer):
    """Validate dashboard layout input."""

    widgets = DashboardLayoutWidgetInputSerializer(many=True)


class DashboardShareInputSerializer(serializers.Serializer):
    """Validate one dashboard share input."""

    target_type = serializers.ChoiceField(choices=DashboardShare.TargetType.choices)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)
    access = serializers.ChoiceField(choices=DashboardShare.Access.choices)

    def validate(self, attrs: dict) -> dict:
        """Validate share target consistency."""
        if attrs["target_type"] == DashboardShare.TargetType.USER and not attrs.get("user_id"):
            raise serializers.ValidationError({"user_id": ["This field is required."]})
        if (
            attrs["target_type"] == DashboardShare.TargetType.PROJECT_MEMBERS
            and not attrs.get("project_id")
        ):
            raise serializers.ValidationError({"project_id": ["This field is required."]})
        return attrs


class DashboardSharesInputSerializer(serializers.Serializer):
    """Validate dashboard shares input."""

    shares = DashboardShareInputSerializer(many=True)


class DashboardRenderInputSerializer(serializers.Serializer):
    """Validate dashboard render input."""

    filters = serializers.DictField(required=False, default=dict)

    def validate_filters(self, value: dict) -> dict:
        """Validate temporary dashboard filters."""
        return validators.validate_task_filters(filters=value, field="filters")


class DashboardRenderEnvelopeSerializer(serializers.Serializer):
    """Serialize dashboard render output."""

    data = serializers.DictField()
