"""Task API filters."""

import django_filters
from django.db.models import Q, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.request import Request

from apps.api.filters import StrictFilterSet, apply_stable_ordering
from apps.tasks.models import Task

TASK_ORDERINGS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "title": "title",
    "-title": "-title",
    "status": "status",
    "-status": "-status",
    "priority": "priority",
    "-priority": "-priority",
    "due_at": "due_at",
    "-due_at": "-due_at",
    "assignee_id": "assignee_id",
    "-assignee_id": "-assignee_id",
}
TASK_FILTER_PARAMETERS = [
    OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("priority", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("assignee_id", OpenApiTypes.INT, OpenApiParameter.QUERY),
    OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("q", OpenApiTypes.STR, OpenApiParameter.QUERY),
    OpenApiParameter("due_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("due_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("created_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("created_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("updated_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("updated_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
    OpenApiParameter("ordering", OpenApiTypes.STR, OpenApiParameter.QUERY),
]


class TaskFilterSet(StrictFilterSet):
    """Filter task querysets with an explicit API whitelist."""

    status = django_filters.ChoiceFilter(choices=Task.Status.choices)
    priority = django_filters.ChoiceFilter(choices=Task.Priority.choices)
    assignee_id = django_filters.NumberFilter(field_name="assignee_id")
    search = django_filters.CharFilter(method="filter_search")
    q = django_filters.CharFilter(method="filter_search")
    due_after = django_filters.IsoDateTimeFilter(field_name="due_at", lookup_expr="gte")
    due_before = django_filters.IsoDateTimeFilter(field_name="due_at", lookup_expr="lte")
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    updated_after = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="lte")

    class Meta:
        """Configure filterset model metadata."""

        model = Task
        fields = [
            "status",
            "priority",
            "assignee_id",
            "search",
            "q",
            "due_after",
            "due_before",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
        ]

    def filter_search(
        self,
        queryset: QuerySet[Task],
        name: str,
        value: str,
    ) -> QuerySet[Task]:
        """Filter tasks by a text search term."""
        normalized_value = value.strip()
        if not normalized_value:
            return queryset
        return queryset.filter(
            Q(title__icontains=normalized_value) | Q(description__icontains=normalized_value)
        )


def filtered_task_queryset(*, request: Request, queryset: QuerySet[Task]) -> QuerySet[Task]:
    """Return a validated and ordered task queryset for a request."""
    filterset = TaskFilterSet(data=request.query_params, queryset=queryset, request=request)
    filtered_queryset = filterset.validated_qs().distinct()
    return apply_stable_ordering(
        queryset=filtered_queryset,
        raw_ordering=request.query_params.get("ordering"),
        allowed_orderings=TASK_ORDERINGS,
        default_ordering="-created_at",
    )
