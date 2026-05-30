"""Unit tests for account user models."""

import pytest
from django.db import IntegrityError, transaction


@pytest.mark.unit
@pytest.mark.django_db
def test_user_uses_email_login_and_normalizes_lowercase():
    """Verify users log in by normalized lowercase email."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email="  Mixed.Case@Example.COM  ",
        password="StrongerPass123!",
        display_name="Mixed Case",
    )

    assert user.USERNAME_FIELD == "email"
    assert user.email == "mixed.case@example.com"
    assert user.display_name == "Mixed Case"
    assert user.check_password("StrongerPass123!")


@pytest.mark.unit
@pytest.mark.django_db
def test_user_model_has_no_username_field():
    """Verify the custom user model does not expose a username field."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    field_names = {field.name for field in User._meta.get_fields()}

    assert "username" not in field_names
    assert not hasattr(User(), "username")


@pytest.mark.unit
@pytest.mark.django_db
def test_user_manager_get_by_natural_key_uses_normalized_email():
    """Verify Django authentication can resolve users by normalized email."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        email="natural@example.com",
        password="StrongerPass123!",
        display_name="Natural Key",
    )

    resolved_user = User.objects.get_by_natural_key(" NATURAL@example.com ")

    assert resolved_user == user


@pytest.mark.unit
@pytest.mark.django_db
def test_duplicate_email_is_rejected_case_insensitively():
    """Verify duplicate emails are rejected regardless of case."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.create_user(
        email="person@example.com",
        password="StrongerPass123!",
        display_name="Person One",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            email="PERSON@example.com",
            password="StrongerPass123!",
            display_name="Person Two",
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_user_profile_defaults_to_utc_timezone():
    """Verify user profiles default to UTC timezone."""
    from django.contrib.auth import get_user_model

    from apps.accounts.models import UserProfile

    User = get_user_model()
    user = User.objects.create_user(
        email="profile@example.com",
        password="StrongerPass123!",
        display_name="Profile User",
    )

    profile = UserProfile.objects.create(user=user)

    assert profile.timezone == "UTC"


@pytest.mark.unit
@pytest.mark.django_db
def test_external_identity_provider_subject_is_unique():
    """Verify external identities are unique by provider and subject."""
    from django.contrib.auth import get_user_model

    from apps.accounts.models import ExternalIdentity

    User = get_user_model()
    user = User.objects.create_user(
        email="identity@example.com",
        password="StrongerPass123!",
        display_name="Identity User",
    )

    ExternalIdentity.objects.create(
        user=user,
        provider="google",
        provider_subject="subject-1",
        email_at_link_time="identity@example.com",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ExternalIdentity.objects.create(
            user=user,
            provider="google",
            provider_subject="subject-1",
            email_at_link_time="other@example.com",
        )
