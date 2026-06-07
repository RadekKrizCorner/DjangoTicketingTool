"""Tests for production monitoring configuration files."""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.kwparametrize(
    {"path": "deploy/monitoring/prometheus/prometheus.yml"},
    {"path": "deploy/monitoring/grafana/provisioning/datasources/prometheus.yml"},
    {"path": "deploy/monitoring/grafana/provisioning/dashboards/dashboards.yml"},
    {"path": "deploy/monitoring/grafana/dashboards/api-overview.json"},
    {"path": "deploy/monitoring/grafana/dashboards/database-performance.json"},
    {"path": "deploy/monitoring/grafana/dashboards/async-jobs.json"},
    {"path": "deploy/monitoring/grafana/dashboards/infrastructure.json"},
)
def test_monitoring_config_files_are_versioned(path):
    """Verify monitoring configuration and dashboard files are committed."""
    assert (REPO_ROOT / path).is_file()


@pytest.mark.kwparametrize(
    {"path": "deploy/monitoring/grafana/dashboards/api-overview.json", "title": "API Overview"},
    {
        "path": "deploy/monitoring/grafana/dashboards/database-performance.json",
        "title": "Database Performance",
    },
    {"path": "deploy/monitoring/grafana/dashboards/async-jobs.json", "title": "Async Jobs"},
    {
        "path": "deploy/monitoring/grafana/dashboards/infrastructure.json",
        "title": "Infrastructure",
    },
)
def test_grafana_dashboards_have_panels_and_prometheus_targets(path, title):
    """Verify Grafana dashboards contain panels backed by Prometheus queries."""
    dashboard = json.loads((REPO_ROOT / path).read_text())

    assert dashboard["title"] == title
    assert dashboard["panels"]
    assert all(panel["targets"] for panel in dashboard["panels"])
    assert all(
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel["targets"]
    )


def test_monitoring_compose_does_not_publish_grafana_publicly():
    """Verify Grafana is reachable through Cloudflare Tunnel, not a public port."""
    compose_text = (REPO_ROOT / "docker-compose.release.monitoring.yml").read_text()

    assert "grafana:" in compose_text
    assert "127.0.0.1:${GRAFANA_LOCAL_PORT:-3000}:3000" in compose_text
    assert "- ${GRAFANA_LOCAL_PORT:-3000}:3000" not in compose_text
    assert "cloudflared:" in compose_text
    assert "http://grafana:3000" in compose_text


def test_monitoring_compose_uses_current_runtime_images():
    """Verify release monitoring uses current pinned runtime images."""
    compose_text = (REPO_ROOT / "docker-compose.release.monitoring.yml").read_text()

    expected_images = [
        "prom/prometheus:v3.12.0",
        "grafana/grafana:13.0.2",
        "quay.io/prometheuscommunity/postgres-exporter:v0.18.1",
        "oliver006/redis_exporter:v1.77.0",
        "quay.io/prometheus/node-exporter:v1.10.2",
        "ghcr.io/google/cadvisor:v0.57.0",
    ]
    retired_images = [
        "prom/prometheus:v2.55.1",
        "grafana/grafana:11.3.1",
        "quay.io/prometheuscommunity/postgres-exporter:v0.15.0",
        "oliver006/redis_exporter:v1.62.0",
        "quay.io/prometheus/node-exporter:v1.8.2",
        "gcr.io/cadvisor/cadvisor:v0.49.1",
    ]

    for image in expected_images:
        assert image in compose_text
    for image in retired_images:
        assert image not in compose_text


def test_monitoring_compose_does_not_require_cloudflare_token_to_parse():
    """Verify monitoring-only Compose commands do not require a tunnel token."""
    compose_text = (REPO_ROOT / "docker-compose.release.monitoring.yml").read_text()

    assert "CLOUDFLARED_TOKEN:?set CLOUDFLARED_TOKEN" not in compose_text
    assert "CLOUDFLARED_TOKEN: ${CLOUDFLARED_TOKEN:-}" in compose_text
    assert "--token ${CLOUDFLARED_TOKEN:-}" in compose_text


def test_prometheus_config_sets_version_3_text_fallbacks():
    """Verify Prometheus 3 scrapes can fall back to the classic text protocol."""
    prometheus_config = (
        REPO_ROOT / "deploy/monitoring/prometheus/prometheus.yml"
    ).read_text()

    assert prometheus_config.count("fallback_scrape_protocol: PrometheusText0.0.4") == 7
