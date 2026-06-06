"""Public homepage integration tests."""

import pytest
from django.test import override_settings

pytestmark = pytest.mark.integration


def test_public_homepage_lists_project_destinations(client):
    """Verify the homepage exposes the required public project links."""
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "Django Ticketing Tool" in html
    assert 'href="/ui/"' in html
    assert 'href="/api/v1/docs/"' in html
    assert 'href="/api/v1/redoc/"' in html
    assert 'href="/api/v1/schema/"' in html
    assert 'href="/docs/"' in html
    assert 'href="/admin/"' in html
    assert 'href="https://github.com/RadekKrizCorner/DjangoTicketingTool"' in html
    assert 'href="https://www.linkedin.com/in/radekkriz/"' in html
    assert "www.radekkriz.space" in html
    assert "www.radekkriz.space:48137" not in html
    assert '<span class="signal-node signal-node-projects">Projects</span>' in html
    assert '<span class="signal-node signal-node-tasks">Tasks</span>' in html
    assert '<span class="signal-node signal-node-notifications">Notifications</span>' in html
    assert "signal-node-api" not in html
    assert "signal-node-docs" not in html
    assert "signal-connectors" not in html
    assert "signal-connector" not in html
    assert "signal-arrow" not in html


def test_public_ui_path_redirects_to_local_ui_service(client):
    """Verify the local UI path forwards to the configured frontend service."""
    response = client.get("/ui/")

    assert response.status_code == 302
    assert response.headers["Location"] == "http://127.0.0.1:5174/"


def test_public_docs_path_redirects_to_local_docs_service(client):
    """Verify the local API docs path forwards to the MkDocs service."""
    response = client.get("/docs/")

    assert response.status_code == 302
    assert response.headers["Location"] == "http://localhost:8001/"


def test_public_homepage_hides_monitoring_link_without_url(client):
    """Verify monitoring links stay hidden until a public Grafana URL is configured."""
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "Grafana Monitoring" not in html
    assert "grafana.radekkriz.space" not in html


@override_settings(PUBLIC_GRAFANA_URL="https://grafana.radekkriz.space")
def test_public_homepage_links_to_cloudflare_access_grafana(client):
    """Verify the homepage can advertise the protected Grafana service."""
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert 'href="https://grafana.radekkriz.space"' in html
    assert "Grafana Monitoring" in html
    assert "Protected dashboards for API, database, async jobs, and host health." in html
