"""Shared API filtering helpers."""

from collections.abc import Mapping

from django.db.models import QuerySet
from django_filters import FilterSet
from rest_framework.exceptions import ValidationError

PAGINATION_QUERY_PARAMS = {"page", "page_size"}


class StrictFilterSet(FilterSet):
    """Validate filtersets before exposing the filtered queryset."""

    ordering_param = "ordering"

    def validated_qs(self) -> QuerySet:
        """Return the queryset after validating all filter parameters."""
        self._validate_supported_query_params()
        if not self.is_valid():
            raise ValidationError(self.errors)
        return self.qs

    def _validate_supported_query_params(self) -> None:
        """Reject query parameters that are not declared filters."""
        supported_params = set(self.filters) | PAGINATION_QUERY_PARAMS | {self.ordering_param}
        unsupported_params = sorted(set(self.data.keys()) - supported_params)
        if unsupported_params:
            raise ValidationError(
                {
                    param: ["Unsupported filter parameter."]
                    for param in unsupported_params
                }
            )


def apply_stable_ordering(
    *,
    queryset: QuerySet,
    raw_ordering: str | None,
    allowed_orderings: Mapping[str, str],
    default_ordering: str,
) -> QuerySet:
    """Apply whitelisted ordering with a deterministic id tie-breaker."""
    ordering_key = raw_ordering or default_ordering
    ordering_field = allowed_orderings.get(ordering_key)
    if ordering_field is None:
        raise ValidationError(
            {
                "ordering": [
                    "Unsupported ordering. Allowed values: "
                    + ", ".join(sorted(allowed_orderings))
                ]
            }
        )

    secondary_ordering = "-id" if ordering_field.startswith("-") else "id"
    if ordering_field.lstrip("-") == "id":
        return queryset.order_by(ordering_field)
    return queryset.order_by(ordering_field, secondary_ordering)
