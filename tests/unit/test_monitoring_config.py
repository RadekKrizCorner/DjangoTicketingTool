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
