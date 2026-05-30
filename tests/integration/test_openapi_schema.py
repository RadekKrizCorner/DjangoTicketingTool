"""Integration tests for public OpenAPI routes."""

import pytest


@pytest.mark.integration
def test_openapi_schema_is_public(client):
    """Verify OpenAPI schema is publicly accessible."""
    response = client.get("/api/v1/schema/")

    assert response.status_code == 200
    assert "openapi" in response.json()


@pytest.mark.integration
def test_swagger_docs_are_public(client):
    """Verify Swagger documentation is publicly accessible."""
    response = client.get("/api/v1/docs/")

    assert response.status_code == 200


@pytest.mark.integration
def test_redoc_docs_are_public(client):
    """Verify Redoc documentation is publicly accessible."""
    response = client.get("/api/v1/redoc/")

    assert response.status_code == 200
