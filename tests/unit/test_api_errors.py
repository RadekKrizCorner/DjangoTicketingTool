"""Unit tests for shared API contracts."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory


class StructuredAPIException(APIException):
    """Represent a structured API exception for handler testing."""

    status_code = 409
    default_code = "conflict"


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_error_view(request):
    """Raise a domain error for exception handler testing."""
    from apps.common.errors import DomainError

    raise DomainError(
        code="project.invalid",
        detail="Project is invalid.",
        field="name",
        status_code=409,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def validation_error_view(request):
    """Raise a native DRF validation error for handler testing."""
    raise ValidationError(
        {
            "name": ["This field is required."],
            "status": ["Invalid status."],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def not_found_view(request):
    """Raise a native DRF not found error for handler testing."""
    raise NotFound("Project was not found.")


@api_view(["GET"])
@permission_classes([AllowAny])
def structured_api_error_view(request):
    """Raise a structured API exception for handler testing."""
    raise StructuredAPIException(
        {
            "detail": "Project is locked.",
            "code": "project_locked",
            "resource": "project",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def paginated_items_view(request):
    """Return paginated in-memory items for paginator testing."""
    from apps.api.pagination import StandardPageNumberPagination

    paginator = StandardPageNumberPagination()
    page = paginator.paginate_queryset(list(range(150)), request)
    return paginator.get_paginated_response(page)


def assert_standard_error(response, field, detail):
    """Verify one standard validation error in a response."""
    assert response.status_code == 400
    assert response.data == {
        "errors": [
            {
                "code": "validation_error",
                "detail": detail,
                "field": field,
            }
        ]
    }


def test_success_response_wraps_data():
    """Verify the success helper wraps payloads in data."""
    from apps.api.responses import success_response

    response = success_response({"status": "ok"})

    assert response.data == {"data": {"status": "ok"}}


def test_domain_error_uses_standard_error_envelope():
    """Verify domain errors use the standard API error envelope."""
    factory = APIRequestFactory()

    response = domain_error_view(factory.get("/domain-error/"))

    assert response.status_code == 409
    assert response.data == {
        "errors": [
            {
                "code": "project.invalid",
                "detail": "Project is invalid.",
                "field": "name",
            }
        ]
    }


def test_drf_validation_error_uses_standard_error_envelope():
    """Verify DRF validation errors use field-specific standard envelopes."""
    factory = APIRequestFactory()

    response = validation_error_view(factory.get("/validation-error/"))

    assert response.status_code == 400
    assert response.data == {
        "errors": [
            {
                "code": "validation_error",
                "detail": "This field is required.",
                "field": "name",
            },
            {
                "code": "validation_error",
                "detail": "Invalid status.",
                "field": "status",
            },
        ]
    }


def test_drf_not_found_error_uses_standard_error_envelope():
    """Verify DRF not found errors use a non-field standard envelope."""
    factory = APIRequestFactory()

    response = not_found_view(factory.get("/not-found/"))

    assert response.status_code == 404
    assert response.data == {
        "errors": [
            {
                "code": "not_found",
                "detail": "Project was not found.",
                "field": None,
            }
        ]
    }


def test_drf_structured_detail_error_uses_non_field_error_envelope():
    """Verify structured DRF detail payloads stay non-field errors."""
    factory = APIRequestFactory()

    response = structured_api_error_view(factory.get("/structured-error/"))

    assert response.status_code == 409
    assert response.data == {
        "errors": [
            {
                "code": "project_locked",
                "detail": "Project is locked.",
                "field": None,
            }
        ]
    }


def test_pagination_returns_standard_default_metadata():
    """Verify paginator returns the default pagination response shape."""
    from apps.api.pagination import StandardPageNumberPagination

    factory = APIRequestFactory()
    request = Request(factory.get("/items/"))
    paginator = StandardPageNumberPagination()

    page = paginator.paginate_queryset(list(range(3)), request)
    response = paginator.get_paginated_response(page)

    assert response.data == {
        "data": [0, 1, 2],
        "meta": {
            "pagination": {
                "count": 3,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
                "next": None,
                "previous": None,
            }
        },
    }


def test_pagination_allows_maximum_page_size():
    """Verify paginator allows the configured maximum page size."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page_size": "100"}))
    pagination = response.data["meta"]["pagination"]

    assert response.status_code == 200
    assert len(response.data["data"]) == 100
    assert pagination["count"] == 150
    assert pagination["page"] == 1
    assert pagination["page_size"] == 100
    assert pagination["total_pages"] == 2
    assert pagination["next"] is not None
    assert pagination["previous"] is None


def test_pagination_rejects_invalid_page():
    """Verify invalid page values return a standard validation error."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page": "abc"}))

    assert_standard_error(response, "page", "Page must be a positive integer.")


def test_pagination_rejects_non_integer_page_size():
    """Verify non-integer page size values return a standard validation error."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page_size": "abc"}))

    assert_standard_error(response, "page_size", "Page size must be a positive integer.")


def test_pagination_rejects_zero_page_size():
    """Verify zero page size values return a standard validation error."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page_size": "0"}))

    assert_standard_error(response, "page_size", "Page size must be a positive integer.")


def test_pagination_rejects_negative_page_size():
    """Verify negative page size values return a standard validation error."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page_size": "-1"}))

    assert_standard_error(response, "page_size", "Page size must be a positive integer.")


def test_pagination_rejects_page_size_above_maximum():
    """Verify oversized page size values return a standard validation error."""
    factory = APIRequestFactory()

    response = paginated_items_view(factory.get("/items/", {"page_size": "101"}))

    assert_standard_error(response, "page_size", "Page size must be less than or equal to 100.")
