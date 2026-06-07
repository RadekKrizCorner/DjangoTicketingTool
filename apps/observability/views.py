"""Views for internal observability endpoints."""

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST

from apps.observability.metrics import prometheus_payload


def metrics_view(_request: HttpRequest) -> HttpResponse:
    """Return Prometheus metrics when explicitly enabled."""
    if not settings.OBSERVABILITY_METRICS_ENABLED:
        raise Http404
    return HttpResponse(prometheus_payload(), content_type=CONTENT_TYPE_LATEST)
