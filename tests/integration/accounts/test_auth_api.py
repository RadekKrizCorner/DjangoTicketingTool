"""Integration tests for account authentication API endpoints."""

import pytest


def _json_post(client, path, payload, headers=None):
    """POST a JSON payload and return the response."""
    headers = headers or {}
    return client.post(path, data=payload, content_type="application/json", **headers)


def _auth_header(access_token):
    """Return a bearer authorization header for a token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


@pytest.mark.integration
@pytest.mark.django_db
def test_register_token_and_me_flow(client):
    """Verify registration, token login, and current-user lookup."""
    register_response = _json_post(
        client,
        "/api/v1/users/register/",
        {
            "email": "Flow.User@Example.COM",
            "password": "StrongerPass123!",
            "password_confirm": "StrongerPass123!",
            "display_name": "Flow User",
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()["data"]["email"] == "flow.user@example.com"

    token_response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": "FLOW.USER@example.com", "password": "StrongerPass123!"},
    )
    token_data = token_response.json()["data"]

    assert token_response.status_code == 200
    assert set(token_data) == {"access", "refresh"}

    me_response = client.get("/api/v1/users/me/", **_auth_header(token_data["access"]))

    assert me_response.status_code == 200
    assert me_response.json()["data"] == {
        "id": register_response.json()["data"]["id"],
        "email": "flow.user@example.com",
        "display_name": "Flow User",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_register_rejects_weak_password(client):
    """Verify registration validates password strength."""
    register_response = _json_post(
        client,
        "/api/v1/users/register/",
        {
            "email": "weak-register@example.com",
            "password": "short",
            "password_confirm": "short",
            "display_name": "Weak Register",
        },
    )

    assert register_response.status_code == 400
    assert register_response.json()["errors"][0]["code"] == "validation_error"
    assert register_response.json()["errors"][0]["field"] == "password"


@pytest.mark.integration
@pytest.mark.django_db
def test_token_refresh_and_verify(client):
    """Verify refresh and verify token endpoints return wrapped data."""
    _json_post(
        client,
        "/api/v1/users/register/",
        {
            "email": "refresh@example.com",
            "password": "StrongerPass123!",
            "password_confirm": "StrongerPass123!",
            "display_name": "Refresh User",
        },
    )
    token_response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": "refresh@example.com", "password": "StrongerPass123!"},
    )
    token_data = token_response.json()["data"]

    refresh_response = _json_post(
        client,
        "/api/v1/users/token/refresh/",
        {"refresh": token_data["refresh"]},
    )
    refreshed_data = refresh_response.json()["data"]

    assert refresh_response.status_code == 200
    assert set(refreshed_data) == {"access", "refresh"}

    verify_response = _json_post(
        client,
        "/api/v1/users/token/verify/",
        {"token": refreshed_data["access"]},
    )

    assert verify_response.status_code == 200
    assert verify_response.json() == {"data": {}}


@pytest.mark.integration
@pytest.mark.django_db
def test_logout_blacklists_refresh_token(client):
    """Verify logout blacklists the submitted refresh token."""
    _json_post(
        client,
        "/api/v1/users/register/",
        {
            "email": "logout@example.com",
            "password": "StrongerPass123!",
            "password_confirm": "StrongerPass123!",
            "display_name": "Logout User",
        },
    )
    token_response = _json_post(
        client,
        "/api/v1/users/token/",
        {"email": "logout@example.com", "password": "StrongerPass123!"},
    )
    token_data = token_response.json()["data"]

    logout_response = _json_post(
        client,
        "/api/v1/users/logout/",
        {"refresh": token_data["refresh"]},
        headers=_auth_header(token_data["access"]),
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"data": {"status": "logged_out"}}

    refresh_response = _json_post(
        client,
        "/api/v1/users/token/refresh/",
        {"refresh": token_data["refresh"]},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()["errors"][0]["code"] == "token_not_valid"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(
        path="/api/v1/users/register/",
        payload={},
        expected_status=400,
    ),
    dict(
        path="/api/v1/users/token/",
        payload={},
        expected_status=400,
    ),
    dict(
        path="/api/v1/users/password-reset/request/",
        payload={"email": "missing@example.com"},
        expected_status=202,
    ),
    dict(
        path="/api/v1/users/password-reset/confirm/",
        payload={},
        expected_status=400,
    ),
)
def test_public_user_endpoints_do_not_require_authentication(
    client,
    path,
    payload,
    expected_status,
):
    """Verify public user endpoints do not require authentication."""
    response = _json_post(client, path, payload)

    assert response.status_code == expected_status
    assert response.json().get("errors", [{}])[0].get("code") != "authentication_required"


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(method="get", path="/api/v1/users/me/", payload=None),
    dict(method="get", path="/api/v1/users/profile/", payload=None),
    dict(method="patch", path="/api/v1/users/profile/", payload={"timezone": "Europe/Prague"}),
    dict(method="get", path="/api/v1/users/search/", payload=None),
    dict(method="get", path="/api/v1/users/personal-tokens/", payload=None),
    dict(method="post", path="/api/v1/users/personal-tokens/", payload={}),
    dict(method="post", path="/api/v1/users/password/", payload={}),
    dict(method="post", path="/api/v1/users/logout/", payload={}),
)
def test_protected_user_endpoints_require_authentication(client, method, path, payload):
    """Verify protected user endpoints require authentication."""
    request = getattr(client, method)
    if payload is None:
        response = request(path)
    else:
        response = request(path, data=payload, content_type="application/json")

    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "authentication_required"
