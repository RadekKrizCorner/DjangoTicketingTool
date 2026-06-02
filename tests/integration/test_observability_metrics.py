"""Observability metrics integration tests."""

import pytest
from django.test import override_settings

pytestmark = pytest.mark.integration


def test_internal_metrics_endpoint_is_disabled_by_default(client):
    """Verify the internal metrics endpoint is not exposed without explicit opt-in."""
    response = client.get("/internal/metrics/")

    assert response.status_code == 404


@override_settings(OBSERVABILITY_METRICS_ENABLED=True)
@pytest.mark.django_db
def test_internal_metrics_endpoint_exports_prometheus_text(client):
    """Verify enabled metrics use the Prometheus text format."""
    response = client.get("/internal/metrics/")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    body = response.content.decode()
    assert "django_http_requests_total" in body
    assert "django_http_request_duration_seconds" in body
    assert "django_db_slow_queries_total" in body
