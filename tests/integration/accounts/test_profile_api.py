"""Integration tests for account profile API endpoints."""

import pytest


def _json_post(client, path, payload, headers=None):
    """POST a JSON payload and return the response."""
    headers = headers or {}
    return client.post(path, data=payload, content_type="application/json", **headers)


def _json_patch(client, path, payload, headers=None):
    """PATCH a JSON payload and return the response."""
    headers = headers or {}
    return client.patch(path, data=payload, content_type="application/json", **headers)


def _auth_header(access_token):
    """Return a bearer authorization header for a token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def _register_and_token(client, email="profile@example.com", password="StrongerPass123!"):
    """Register a user and return token data."""
    _json_post(
        client,
        "/api/v1/users/register/",
        {
            "email": email,
            "password": password,
            "password_confirm": password,
            "display_name": "Profile User",
        },
    )
    response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": email, "password": password},
    )
    return response.json()["data"]


@pytest.mark.integration
@pytest.mark.django_db
def test_profile_get_and_patch(client):
    """Verify authenticated users can read and update their profile."""
    token_data = _register_and_token(client)
    headers = _auth_header(token_data["access"])

    get_response = client.get("/api/v1/users/profile/", **headers)
    patch_response = _json_patch(
        client,
        "/api/v1/users/profile/",
        {"timezone": "Europe/Prague"},
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json() == {"data": {"timezone": "UTC"}}
    assert patch_response.status_code == 200
    assert patch_response.json() == {"data": {"timezone": "Europe/Prague"}}


@pytest.mark.integration
@pytest.mark.django_db
def test_password_change_succeeds_with_old_password(client):
    """Verify password change succeeds with the current password."""
    token_data = _register_and_token(client, email="change@example.com", password="OldPass123!")
    headers = _auth_header(token_data["access"])

    response = _json_post(
        client,
        "/api/v1/users/password/",
        {
            "old_password": "OldPass123!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "password_changed"}}

    login_response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": "change@example.com", "password": "NewPass123!"},
    )

    assert login_response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
def test_password_change_rejects_wrong_old_password(client):
    """Verify password change rejects an incorrect current password."""
    token_data = _register_and_token(client, email="wrong-old@example.com", password="OldPass123!")
    headers = _auth_header(token_data["access"])

    response = _json_post(
        client,
        "/api/v1/users/password/",
        {
            "old_password": "WrongPass123!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "old_password"


@pytest.mark.integration
@pytest.mark.django_db
def test_password_change_rejects_weak_new_password(client):
    """Verify password change validates new password strength."""
    token_data = _register_and_token(
        client,
        email="weak-change@example.com",
        password="OldPass123!",
    )
    headers = _auth_header(token_data["access"])

    response = _json_post(
        client,
        "/api/v1/users/password/",
        {
            "old_password": "OldPass123!",
            "new_password": "short",
            "new_password_confirm": "short",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == "new_password"
