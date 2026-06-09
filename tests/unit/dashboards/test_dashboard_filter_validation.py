"""Unit tests for dashboard filter validation."""

import pytest

from apps.common.errors import DomainError
from apps.dashboards.validators import validate_task_filters
from apps.tasks.models import Task


def test_validate_task_filters_rejects_string_id_lists() -> None:
    """Verify ID filters must be lists of numeric IDs."""
    with pytest.raises(DomainError) as error:
        validate_task_filters(filters={"project_ids": "abc"}, field="filters")

    assert error.value.field == "filters"
    assert "project_ids" in error.value.detail


def test_validate_task_filters_rejects_unknown_statuses() -> None:
    """Verify status filters are limited to task status choices."""
    with pytest.raises(DomainError) as error:
        validate_task_filters(filters={"statuses": ["not_real"]}, field="filters")

    assert error.value.field == "filters"
    assert "statuses" in error.value.detail


def test_validate_task_filters_rejects_unknown_due_windows() -> None:
    """Verify due filters are limited to known dashboard windows."""
    with pytest.raises(DomainError) as error:
        validate_task_filters(filters={"due_window": "next_year"}, field="filters")

    assert error.value.field == "filters"
    assert "due_window" in error.value.detail


def test_validate_task_filters_normalizes_supported_values() -> None:
    """Verify supported dashboard filters are returned unchanged."""
    filters = validate_task_filters(
        filters={
            "project_ids": [10],
            "statuses": [Task.Status.IN_PROGRESS],
            "priorities": [Task.Priority.URGENT],
            "assignee_ids": [20],
            "due_window": "next_7_days",
        },
        field="filters",
    )

    assert filters == {
        "project_ids": [10],
        "statuses": [Task.Status.IN_PROGRESS],
        "priorities": [Task.Priority.URGENT],
        "assignee_ids": [20],
        "due_window": "next_7_days",
    }
