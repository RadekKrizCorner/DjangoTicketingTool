"""Tests for the initial Django project bootstrap."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.urls import get_resolver

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _read_production_setting(setting_name):
    """Read one production setting in a clean subprocess."""
    env = os.environ.copy()
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env["DJANGO_ALLOWED_HOSTS"] = "example.test"
    env["DJANGO_SECRET_KEY"] = "subprocess-test-secret"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json;"
                "from config.settings import production;"
                f"print(json.dumps(getattr(production, '{setting_name}')))"
            ),
        ],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )
    return json.loads(result.stdout)


def _read_release_allowed_hosts_default():
    """Read the release compose default allowed hosts value."""
    compose_text = (REPO_ROOT / "docker-compose.release.yml").read_text()
    allowed_hosts_pattern = (
        r"DJANGO_ALLOWED_HOSTS: \$\{DJANGO_ALLOWED_HOSTS:-(?P<hosts>[^}]+)\}"
    )
    match = re.search(allowed_hosts_pattern, compose_text)
    assert match is not None
    return match.group("hosts").split(",")


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


def test_production_health_paths_are_ssl_redirect_exempt():
    """Verify production exempts exact health probe paths from SSL redirects."""
    exemptions = _read_production_setting("SECURE_REDIRECT_EXEMPT")

    assert exemptions == [
        r"^api/v1/health/live/$",
        r"^api/v1/health/ready/$",
    ]
    assert any(re.match(pattern, "api/v1/health/live/") for pattern in exemptions)
    assert any(re.match(pattern, "api/v1/health/ready/") for pattern in exemptions)
    assert not any(re.match(pattern, "api/v1/health/live/extra") for pattern in exemptions)
    assert not any(re.match(pattern, "api/v1/health/ready/extra") for pattern in exemptions)


def test_release_compose_defaults_accept_public_cloudflare_hosts():
    """Verify release compose defaults accept the Cloudflare public hosts."""
    default_hosts = _read_release_allowed_hosts_default()

    assert "radekkriz.space" in default_hosts
    assert "www.radekkriz.space" in default_hosts
    assert "localhost" in default_hosts
    assert "127.0.0.1" in default_hosts
    assert "api" in default_hosts
