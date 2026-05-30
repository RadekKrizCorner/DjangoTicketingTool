"""Integration tests for health API endpoints."""

import pytest
from django.test import override_settings

from apps.health.api import views as health_views


def passing_probe():
    """Run a successful dependency probe."""


def failing_probe():
    """Run a failed dependency probe."""
    raise RuntimeError("dependency unavailable")


@pytest.mark.integration
def test_live_health_is_public(client):
    """Verify live health endpoint is public."""
    response = client.get("/api/v1/health/live/")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


@pytest.mark.integration
@pytest.mark.django_db
def test_ready_health_returns_dependency_status(client):
    """Verify ready health endpoint returns dependency status."""
    response = client.get("/api/v1/health/ready/")
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.integration
def test_ready_health_returns_error_when_database_fails(client, monkeypatch):
    """Verify readiness reports database failure deterministically."""
    monkeypatch.setattr(health_views, "_check_database", failing_probe)
    monkeypatch.setattr(health_views, "_check_redis", passing_probe)

    response = client.get("/api/v1/health/ready/")
    data = response.json()["data"]

    assert response.status_code == 503
    assert data["status"] == "error"
    assert data["database"] == "error"
    assert data["redis"] == "ok"


@pytest.mark.integration
def test_ready_health_returns_error_when_redis_fails(client, monkeypatch):
    """Verify readiness reports Redis failure deterministically."""
    monkeypatch.setattr(health_views, "_check_database", passing_probe)
    monkeypatch.setattr(health_views, "_check_redis", failing_probe)

    response = client.get("/api/v1/health/ready/")
    data = response.json()["data"]

    assert response.status_code == 503
    assert data["status"] == "error"
    assert data["database"] == "ok"
    assert data["redis"] == "error"


def test_redis_readiness_url_prefers_health_redis_url():
    """Verify readiness uses the explicit health Redis URL first."""
    with override_settings(
        HEALTH_REDIS_URL="redis://health:6379/9",
        REDIS_URL="redis://redis:6379/0",
        CELERY_BROKER_URL="redis://broker:6379/1",
    ):
        assert health_views.redis_readiness_url() == "redis://health:6379/9"


def test_redis_readiness_url_falls_back_to_redis_url():
    """Verify readiness uses Redis URL when health Redis URL is empty."""
    with override_settings(
        HEALTH_REDIS_URL="",
        REDIS_URL="redis://redis:6379/0",
        CELERY_BROKER_URL="redis://broker:6379/1",
    ):
        assert health_views.redis_readiness_url() == "redis://redis:6379/0"


def test_redis_readiness_url_falls_back_to_celery_broker_url():
    """Verify readiness uses Celery broker URL when Redis URLs are empty."""
    with override_settings(
        HEALTH_REDIS_URL="",
        REDIS_URL="",
        CELERY_BROKER_URL="redis://broker:6379/1",
    ):
        assert health_views.redis_readiness_url() == "redis://broker:6379/1"
