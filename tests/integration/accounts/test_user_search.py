"""Integration tests for account user search API endpoints."""

import pytest


def _json_post(client, path, payload):
    """POST a JSON payload and return the response."""
    return client.post(path, data=payload, content_type="application/json")


def _auth_header(access_token):
    """Return a bearer authorization header for a token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def _create_user(email, display_name, password="StrongerPass123!", is_active=True):
    """Create a user for search tests."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email=email,
        password=password,
        display_name=display_name,
        is_active=is_active,
    )


def _token_for(client, email, password="StrongerPass123!"):
    """Return JWT token data for a user."""
    response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": email, "password": password},
    )
    return response.json()["data"]


def _resolve_ref(schema, value):
    """Resolve a local OpenAPI schema reference."""
    reference = value.get("$ref")
    if reference is None:
        return value
    component_name = reference.removeprefix("#/components/schemas/")
    return schema["components"]["schemas"][component_name]


@pytest.mark.integration
@pytest.mark.django_db
def test_user_search_filters_active_users_by_term_and_returns_minimal_fields(client):
    """Verify user search filters active users and returns minimal fields."""
    actor = _create_user("actor@example.com", "Actor User")
    alice = _create_user("alice@example.com", "Alice Adams")
    _create_user("inactive-alice@example.com", "Inactive Alice", is_active=False)
    _create_user("bob@example.com", "Bob Builder")
    token_data = _token_for(client, actor.email)

    response = client.get(
        "/api/v1/users/search/",
        {"q": "ali"},
        **_auth_header(token_data["access"]),
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["data"] == [
        {
            "id": alice.id,
            "email": "alice@example.com",
            "display_name": "Alice Adams",
        }
    ]
    assert set(payload["data"][0]) == {"id", "email", "display_name"}


@pytest.mark.integration
def test_user_search_schema_documents_pagination_metadata(client):
    """Verify user search OpenAPI response documents pagination metadata."""
    schema = client.get("/api/v1/schema/").json()
    response_schema = schema["paths"]["/api/v1/users/search/"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    resolved_schema = _resolve_ref(schema, response_schema)
    meta_schema = _resolve_ref(schema, resolved_schema["properties"]["meta"])

    assert "meta" in resolved_schema["properties"]
    assert "pagination" in meta_schema["properties"]
