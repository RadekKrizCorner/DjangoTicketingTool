"""Integration tests for personal access token API endpoints."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import PersonalAccessToken
from tests.factories import auth_header, create_user


def _json_post(client, path: str, payload: dict, headers: dict | None = None):
    """POST JSON and return the response."""
    return client.post(
        path,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


def _json_patch(client, path: str, payload: dict, headers: dict | None = None):
    """PATCH JSON and return the response."""
    return client.patch(
        path,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


def _pat_header(token: str) -> dict[str, str]:
    """Return a bearer header for a personal access token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.django_db
def test_personal_access_token_create_list_and_revoke(client):
    """Verify users can create, list, and revoke their own personal access tokens."""
    user = create_user(email="pat-owner@example.com")
    headers = auth_header(user)
    expires_at = (timezone.now() + timedelta(days=30)).isoformat()

    create_response = _json_post(
        client,
        "/api/v1/users/personal-tokens/",
        {
            "name": "Postman",
            "scopes": ["full_access"],
            "expires_at": expires_at,
        },
        headers=headers,
    )

    assert create_response.status_code == 201
    token_data = create_response.json()["data"]
    raw_token = token_data["token"]
    stored_token = PersonalAccessToken.objects.get(user=user)

    assert raw_token.startswith("rkriz_pat_")
    assert token_data["token_prefix"] == raw_token[:20]
    assert stored_token.token_hash != raw_token
    assert stored_token.token_prefix == raw_token[:20]

    list_response = client.get("/api/v1/users/personal-tokens/", **headers)

    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["name"] == "Postman"
    assert "token" not in list_response.json()["data"][0]

    revoke_response = client.delete(
        f"/api/v1/users/personal-tokens/{stored_token.id}/",
        **headers,
    )

    assert revoke_response.status_code == 204
    stored_token.refresh_from_db()
    assert stored_token.revoked_at is not None


@pytest.mark.integration
@pytest.mark.django_db
def test_full_access_personal_access_token_authenticates_api_requests(client):
    """Verify full-access personal access tokens authenticate API requests."""
    user = create_user(email="pat-full@example.com")
    create_response = _json_post(
        client,
        "/api/v1/users/personal-tokens/",
        {"name": "Python script", "scopes": ["full_access"]},
        headers=auth_header(user),
    )
    raw_token = create_response.json()["data"]["token"]

    me_response = client.get("/api/v1/users/me/", **_pat_header(raw_token))

    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "pat-full@example.com"
    stored_token = PersonalAccessToken.objects.get(user=user)
    assert stored_token.last_used_at is not None


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(method="get", path="/api/v1/users/me/", payload=None, expected_status=200),
    dict(
        method="patch",
        path="/api/v1/users/profile/",
        payload={"timezone": "Europe/Prague"},
        expected_status=403,
    ),
    dict(
        method="post",
        path="/api/v1/users/personal-tokens/",
        payload={"name": "Nested", "scopes": ["full_access"]},
        expected_status=403,
    ),
)
def test_read_only_personal_access_token_allows_only_safe_methods(
    client,
    method,
    path,
    payload,
    expected_status,
):
    """Verify read-only personal access tokens cannot mutate API state."""
    user = create_user(email="pat-readonly@example.com")
    create_response = _json_post(
        client,
        "/api/v1/users/personal-tokens/",
        {"name": "Read only", "scopes": ["read_only"]},
        headers=auth_header(user),
    )
    raw_token = create_response.json()["data"]["token"]
    request = getattr(client, method)

    if payload is None:
        response = request(path, **_pat_header(raw_token))
    else:
        response = request(
            path,
            data=payload,
            content_type="application/json",
            **_pat_header(raw_token),
        )

    assert response.status_code == expected_status


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(case="revoked"),
    dict(case="expired"),
)
def test_unusable_personal_access_tokens_are_rejected(client, case):
    """Verify revoked and expired personal access tokens cannot authenticate."""
    user = create_user(email=f"pat-{case}@example.com")
    expires_at = None
    if case == "expired":
        expires_at = (timezone.now() + timedelta(days=1)).isoformat()
    create_response = _json_post(
        client,
        "/api/v1/users/personal-tokens/",
        {
            "name": case.title(),
            "scopes": ["full_access"],
            "expires_at": expires_at,
        },
        headers=auth_header(user),
    )
    raw_token = create_response.json()["data"]["token"]
    stored_token = PersonalAccessToken.objects.get(user=user)
    if case == "revoked":
        stored_token.revoked_at = timezone.now()
    else:
        stored_token.expires_at = timezone.now() - timedelta(minutes=1)
    stored_token.save(update_fields=["revoked_at", "expires_at"])

    response = client.get("/api/v1/users/me/", **_pat_header(raw_token))

    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "token_not_valid"


@pytest.mark.integration
@pytest.mark.django_db
def test_users_cannot_revoke_other_users_personal_access_tokens(client):
    """Verify users cannot revoke personal access tokens owned by another user."""
    owner = create_user(email="pat-owned@example.com")
    actor = create_user(email="pat-attacker@example.com")
    create_response = _json_post(
        client,
        "/api/v1/users/personal-tokens/",
        {"name": "Owned", "scopes": ["full_access"]},
        headers=auth_header(owner),
    )
    token_id = create_response.json()["data"]["id"]

    response = client.delete(
        f"/api/v1/users/personal-tokens/{token_id}/",
        **auth_header(actor),
    )

    assert response.status_code == 404
