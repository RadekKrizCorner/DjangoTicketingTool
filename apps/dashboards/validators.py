"""Dashboard input validators."""

from http import HTTPStatus
from typing import Any

from apps.common.errors import DomainError
from apps.tasks.models import Task

TASK_FILTER_KEYS = {"project_ids", "statuses", "priorities", "assignee_ids", "due_window"}
ID_LIST_FILTER_KEYS = {"project_ids", "assignee_ids"}
DUE_WINDOWS = {"overdue", "next_24_hours", "next_7_days"}


def validate_task_filters(*, filters: dict, field: str) -> dict:
    """Return normalized dashboard task filters."""
    if not isinstance(filters, dict):
        raise_validation_error(field=field, detail="Dashboard filters must be an object.")

    unsupported_keys = sorted(set(filters) - TASK_FILTER_KEYS)
    if unsupported_keys:
        raise_validation_error(
            field=field,
            detail=f"Unsupported dashboard filter keys: {', '.join(unsupported_keys)}.",
        )

    normalized = {}
    for key, value in filters.items():
        if is_empty_filter_value(value):
            continue
        if key in ID_LIST_FILTER_KEYS:
            normalized[key] = validate_integer_list(key=key, value=value, field=field)
        elif key == "statuses":
            normalized[key] = validate_choice_list(
                key=key,
                value=value,
                field=field,
                choices=set(Task.Status.values),
            )
        elif key == "priorities":
            normalized[key] = validate_choice_list(
                key=key,
                value=value,
                field=field,
                choices=set(Task.Priority.values),
            )
        elif key == "due_window":
            normalized[key] = validate_due_window(value=value, field=field)
    return normalized


def is_empty_filter_value(value: Any) -> bool:
    """Return whether a filter value should be ignored."""
    return value in (None, "", "all", [])


def validate_integer_list(*, key: str, value: Any, field: str) -> list[int]:
    """Return a validated positive integer list."""
    if not isinstance(value, list):
        raise_validation_error(field=field, detail=f"{key} must be a list of positive integer IDs.")

    normalized = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise_validation_error(
                field=field,
                detail=f"{key} must be a list of positive integer IDs.",
            )
        normalized.append(item)
    return normalized


def validate_choice_list(*, key: str, value: Any, field: str, choices: set[str]) -> list[str]:
    """Return a validated list of choice strings."""
    if not isinstance(value, list):
        raise_validation_error(field=field, detail=f"{key} must be a list of supported values.")

    normalized = []
    for item in value:
        if not isinstance(item, str) or item not in choices:
            raise_validation_error(field=field, detail=f"{key} contains an unsupported value.")
        normalized.append(item)
    return normalized


def validate_due_window(*, value: Any, field: str) -> str:
    """Return a validated dashboard due-date window."""
    if not isinstance(value, str) or value not in DUE_WINDOWS:
        raise_validation_error(field=field, detail="due_window contains an unsupported value.")
    return value


def raise_validation_error(*, field: str, detail: str) -> None:
    """Raise a dashboard validation error."""
    raise DomainError(
        code="validation_error",
        detail=detail,
        field=field,
        status_code=HTTPStatus.BAD_REQUEST,
    )
