"""Integration tests for password reset API endpoints."""

import pytest
from django.core import mail


def _json_post(client, path, payload):
    """POST a JSON payload and return the response."""
    return client.post(path, data=payload, content_type="application/json")


def _create_user(email, password="StrongerPass123!", display_name="Reset User"):
    """Create a test user with a local password."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email=email, password=password, display_name=display_name)


def _reset_credentials(user):
    """Return a valid password reset uid and token for a user."""
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    from apps.accounts.tokens import password_reset_token_generator

    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": password_reset_token_generator.make_token(user),
    }


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.kwparametrize(
    dict(case_name="missing", email="missing@example.com", create_kind=None, expected_mail_count=0),
    dict(
        case_name="usable",
        email="usable@example.com",
        create_kind="usable",
        expected_mail_count=1,
    ),
    dict(
        case_name="unusable",
        email="sso@example.com",
        create_kind="unusable",
        expected_mail_count=0,
    ),
)
def test_password_reset_request_hides_account_state(
    client,
    case_name,
    email,
    create_kind,
    expected_mail_count,
):
    """Verify reset request hides missing and unusable-password accounts."""
    if create_kind == "usable":
        _create_user(email=email)
    elif create_kind == "unusable":
        user = _create_user(email=email)
        user.set_unusable_password()
        user.save(update_fields=["password"])

    response = _json_post(
        client,
        "/api/v1/users/password-reset/request/",
        {"email": email.upper()},
    )

    assert case_name
    assert response.status_code == 202
    assert response.json() == {"data": {"status": "accepted"}}
    assert len(mail.outbox) == expected_mail_count


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_confirm_changes_password(client):
    """Verify a valid password reset confirmation changes the password."""
    user = _create_user(email="confirm@example.com", password="OldPass123!")
    credentials = _reset_credentials(user)

    response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "password_reset"}}
    assert user.check_password("NewPass123!")


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_confirm_rejects_invalid_token(client):
    """Verify an invalid password reset token returns a standard error."""
    user = _create_user(email="invalid-token@example.com")
    credentials = _reset_credentials(user)

    response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "token": "invalid-token",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "password_reset_invalid"


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_confirm_rejects_base64_valid_non_integer_uid(client):
    """Verify a non-integer decoded uid returns a standard reset error."""
    response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            "uid": "YWJj",
            "token": "token",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "password_reset_invalid"


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_request_accepts_existing_user_when_email_send_fails(client, monkeypatch):
    """Verify reset request does not leak account existence on mail failure."""
    _create_user(email="mail-failure@example.com")

    def failing_send_mail(*args, **kwargs):
        """Raise an email backend failure."""
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr("apps.accounts.services.send_mail", failing_send_mail)

    response = _json_post(
        client,
        "/api/v1/users/password-reset/request/",
        {"email": "mail-failure@example.com"},
    )

    assert response.status_code == 202
    assert response.json() == {"data": {"status": "accepted"}}


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_confirm_rejects_password_mismatch(client):
    """Verify password reset confirmation rejects mismatched passwords."""
    user = _create_user(email="mismatch@example.com")
    credentials = _reset_credentials(user)

    response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "new_password": "NewPass123!",
            "new_password_confirm": "OtherPass123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == "new_password_confirm"


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_confirm_rejects_weak_password(client):
    """Verify password reset confirmation validates password strength."""
    user = _create_user(email="weak-reset@example.com")
    credentials = _reset_credentials(user)

    response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "new_password": "short",
            "new_password_confirm": "short",
        },
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == "new_password"


@pytest.mark.integration
@pytest.mark.django_db
def test_password_reset_token_reuse_fails(client):
    """Verify a password reset token cannot be reused after success."""
    user = _create_user(email="reuse@example.com", password="OldPass123!")
    credentials = _reset_credentials(user)

    first_response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
    )
    second_response = _json_post(
        client,
        "/api/v1/users/password-reset/confirm/",
        {
            **credentials,
            "new_password": "AnotherPass123!",
            "new_password_confirm": "AnotherPass123!",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["errors"][0]["code"] == "password_reset_invalid"
