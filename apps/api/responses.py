"""Shared API response helpers."""

from typing import Any

from rest_framework.response import Response


def success_response(
    data: Any,
    status_code: int | None = None,
    headers: dict | None = None,
) -> Response:
    """Return a standard success response."""
    return Response({"data": data}, status=status_code, headers=headers)
