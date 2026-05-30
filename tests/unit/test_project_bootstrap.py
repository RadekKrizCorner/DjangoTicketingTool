"""Tests for the initial Django project bootstrap."""

import os
import subprocess
import sys

from django.conf import settings
from django.urls import get_resolver


def _import_module_without_settings(module_name):
    """Import a module without a selected settings module."""
    env = os.environ.copy()
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env["DJANGO_ALLOWED_HOSTS"] = "example.test"
    env["DJANGO_SECRET_KEY"] = "subprocess-test-secret"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib, os;"
                f"importlib.import_module('{module_name}');"
                "print(os.environ.get('DJANGO_SETTINGS_MODULE'))"
            ),
        ],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )
    return result.stdout.strip()


def test_django_settings_load():
    """Verify Django settings load for the test suite."""
    assert settings.ROOT_URLCONF == "config.urls"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_api_v1_prefix_is_registered():
    """Verify the API v1 URL prefix is registered."""
    routes = {
        getattr(pattern.pattern, "_route", str(pattern.pattern))
        for pattern in get_resolver().url_patterns
    }

    assert "api/v1/" in routes


def test_live_health_endpoint_returns_ok(client):
    """Verify the live health endpoint returns an ok response."""
    response = client.get("/api/v1/health/live/")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


def test_runtime_entrypoints_default_to_production_settings():
    """Verify runtime entrypoints default to production settings."""
    for module_name in ("config.asgi", "config.celery", "config.wsgi"):
        assert _import_module_without_settings(module_name) == "config.settings.production"


def test_test_settings_define_explicit_database_strategy():
    """Verify test settings define their own database strategy."""
    database = settings.DATABASES["default"]

    assert database["CONN_MAX_AGE"] == 0
    assert database["TEST"]["NAME"] == "test_app"
