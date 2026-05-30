"""Shared API exception handling."""

from typing import Any

from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.errors import DomainError

DEFAULT_ERROR_CODE = "error"
VALIDATION_ERROR_CODE = "validation_error"
ERROR_CODE_MAP = {
    "not_authenticated": "authentication_required",
    "permission_denied": "permission_denied",
    "not_found": "not_found",
}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Return standard error envelopes for handled API exceptions."""
    if isinstance(exc, DomainError):
        return Response(
            {"errors": [_error_item(exc.code, exc.detail, exc.field)]},
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    response.data = {"errors": _normalize_errors(response.data)}
    return response


def _normalize_errors(data: Any) -> list[dict[str, Any]]:
    """Convert DRF error payloads into standard error items."""
    if isinstance(data, dict):
        if "detail" in data:
            return [_detail_error_item(data)]

        errors: list[dict[str, Any]] = []
        for field, value in data.items():
            errors.extend(_iter_error_items(value, str(field)))
        return errors or [_error_item(DEFAULT_ERROR_CODE, str(data), None)]

    if isinstance(data, list):
        errors = []
        for value in data:
            errors.extend(_iter_error_items(value, None))
        return errors or [_error_item(DEFAULT_ERROR_CODE, str(data), None)]

    return list(_iter_error_items(data, None))


def _iter_error_items(value: Any, field: str | None) -> list[dict[str, Any]]:
    """Return standard error items for one DRF error value."""
    if isinstance(value, dict):
        errors: list[dict[str, Any]] = []
        for key, child in value.items():
            child_field = f"{field}.{key}" if field else str(key)
            errors.extend(_iter_error_items(child, child_field))
        return errors

    if isinstance(value, list):
        errors = []
        for child in value:
            errors.extend(_iter_error_items(child, field))
        return errors

    code = _error_code(value, field)
    return [_error_item(code, str(value), field)]


def _error_code(value: Any, field: str | None) -> str:
    """Return the standard error code for one error value."""
    if isinstance(value, ErrorDetail):
        mapped_code = ERROR_CODE_MAP.get(value.code)
        if mapped_code:
            return mapped_code
        if field is not None:
            return VALIDATION_ERROR_CODE
        return str(value.code)

    if field is not None:
        return VALIDATION_ERROR_CODE
    return DEFAULT_ERROR_CODE


def _detail_error_item(data: dict[str, Any]) -> dict[str, Any]:
    """Return a non-field error item for a detail payload."""
    detail = data["detail"]
    code = _metadata_code(data.get("code")) or _error_code(detail, None)
    return _error_item(code, str(detail), None)


def _metadata_code(value: Any) -> str | None:
    """Return a stable string code from optional error metadata."""
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return _metadata_code(value[0])
    return str(value)


def _error_item(code: str, detail: str, field: str | None) -> dict[str, Any]:
    """Return one standard error item."""
    return {"code": code, "detail": detail, "field": field}
