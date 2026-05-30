"""Shared API pagination helpers."""

from typing import Any

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

PAGE_ERROR = "Page must be a positive integer."
PAGE_SIZE_ERROR = "Page size must be a positive integer."
PAGE_SIZE_MAX_ERROR = "Page size must be less than or equal to 100."


class StandardPageNumberPagination(PageNumberPagination):
    """Paginate list endpoints with the standard response envelope."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(
        self,
        queryset: Any,
        request: Any,
        view: Any | None = None,
    ) -> list[Any] | None:
        """Return a page or raise standard validation errors for invalid input."""
        try:
            return super().paginate_queryset(queryset, request, view)
        except NotFound as exc:
            raise ValidationError({"page": ["Invalid page."]}) from exc

    def get_page_number(self, request: Any, paginator: Any) -> int:
        """Return a validated positive page number."""
        page_number = request.query_params.get(self.page_query_param, 1)
        try:
            page_number = int(page_number)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"page": [PAGE_ERROR]}) from exc

        if page_number < 1:
            raise ValidationError({"page": [PAGE_ERROR]})
        return page_number

    def get_page_size(self, request: Any) -> int:
        """Return a validated positive page size."""
        raw_page_size = request.query_params.get(self.page_size_query_param)
        if raw_page_size is None:
            return self.page_size

        try:
            page_size = int(raw_page_size)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"page_size": [PAGE_SIZE_ERROR]}) from exc

        if page_size < 1:
            raise ValidationError({"page_size": [PAGE_SIZE_ERROR]})
        if page_size > self.max_page_size:
            raise ValidationError({"page_size": [PAGE_SIZE_MAX_ERROR]})
        return page_size

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return the standard paginated response."""
        return Response(
            {
                "data": data,
                "meta": {
                    "pagination": {
                        "count": self.page.paginator.count,
                        "page": self.page.number,
                        "page_size": self.page.paginator.per_page,
                        "total_pages": self.page.paginator.num_pages,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    }
                },
            }
        )
