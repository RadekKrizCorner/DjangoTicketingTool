"""Health API views."""

from django.http import JsonResponse
from django.http.request import HttpRequest


def live_health(request: HttpRequest) -> JsonResponse:
    """Return the live health status."""
    return JsonResponse({"data": {"status": "ok"}})
