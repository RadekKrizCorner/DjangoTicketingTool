"""Project API filters."""

import django_filters
from django.db.models import Q, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.request import Request

from apps.api.filters import StrictFilterSet, apply_stable_ordering
from apps.projects.models import Project, ProjectMembership

PROJECT_ORDERINGS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "name": "name",
    "-name": "-name",
    "visibility": "visibility",
    "-visibility": "-visibility",
    "state": "state",
    "-state": "-state",
    "owner_id": "owner_id",
    "-owner_id": "-owner_id",
}
PROJECT_FILTER_PARAMETERS = [
    OpenApiParameter("visibility", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("state", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("role", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("owner_id", OpenApiTypes.INT, OpenApiParameter.QUERY),
    OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("q", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("created_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("created_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("updated_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("updated_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("ordering", OpenApiTypes.STR, OpenApiParameter.QUERY),
]


class ProjectFilterSet(StrictFilterSet):
    """Filter visible project querysets with an explicit API whitelist."""

    visibility = django_filters.ChoiceFilter(choices=Project.Visibility.choices)
    state = django_filters.ChoiceFilter(choices=Project.State.choices)
    role = django_filters.ChoiceFilter(
        choices=ProjectMembership.Role.choices,
        method="filter_role",
    )
    owner_id = django_filters.NumberFilter(field_name="owner_id")
    search = django_filters.CharFilter(method="filter_search")
    q = django_filters.CharFilter(method="filter_search")
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    updated_after = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="lte")

    class Meta:
        """Configure filterset model metadata."""

        model = Project
        fields = [
            "visibility",
            "state",
            "role",
            "owner_id",
            "search",
            "q",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
        ]

    def filter_role(self, queryset: QuerySet[Project], name: str, value: str) -> QuerySet[Project]:
        """Filter projects by the requesting user's project role."""
        return queryset.filter(
            memberships__user=self.request.user,
            memberships__role=value,
            memberships__deleted_at__isnull=True,
        )

    def filter_search(
        self,
        queryset: QuerySet[Project],
        name: str,
        value: str,
    ) -> QuerySet[Project]:
        """Filter projects by a text search term."""
        normalized_value = value.strip()
        if not normalized_value:
            return queryset
        return queryset.filter(
            Q(name__icontains=normalized_value) | Q(description__icontains=normalized_value)
        )


def filtered_project_queryset(
    *,
    request: Request,
    queryset: QuerySet[Project],
) -> QuerySet[Project]:
    """Return a validated and ordered project queryset for a request."""
    filterset = ProjectFilterSet(data=request.query_params, queryset=queryset, request=request)
    filtered_queryset = filterset.validated_qs().distinct()
    return apply_stable_ordering(
        queryset=filtered_queryset,
        raw_ordering=request.query_params.get("ordering"),
        allowed_orderings=PROJECT_ORDERINGS,
        default_ordering="-created_at",
    )
