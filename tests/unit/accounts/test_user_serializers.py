"""Unit tests for account API serializers."""

import pytest

from apps.accounts.api.serializers import (
    PasswordResetRequestInputSerializer,
    RegisterInputSerializer,
)


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(
        serializer_class=RegisterInputSerializer,
        payload={
            "email": "  Mixed.Register@Example.COM  ",
            "password": "StrongerPass123!",
            "password_confirm": "StrongerPass123!",
            "display_name": "Mixed Register",
        },
        expected_email="mixed.register@example.com",
    ),
    dict(
        serializer_class=PasswordResetRequestInputSerializer,
        payload={"email": "  Mixed.Reset@Example.COM  "},
        expected_email="mixed.reset@example.com",
    ),
)
def test_email_input_serializers_normalize_email(serializer_class, payload, expected_email):
    """Verify email normalization happens at the API serializer boundary."""
    serializer = serializer_class(data=payload)

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["email"] == expected_email
