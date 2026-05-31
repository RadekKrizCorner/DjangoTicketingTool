"""Public homepage integration tests."""

import pytest

pytestmark = pytest.mark.integration


def test_public_homepage_lists_project_destinations(client):
    """Verify the homepage exposes the required public project links."""
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "Django Ticketing Tool" in html
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


def test_public_docs_path_redirects_to_local_docs_service(client):
    """Verify the local API docs path forwards to the MkDocs service."""
    response = client.get("/docs/")

    assert response.status_code == 302
    assert response.headers["Location"] == "http://localhost:8001/"
