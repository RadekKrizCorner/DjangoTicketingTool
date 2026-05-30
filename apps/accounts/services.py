"""Account business services."""

import logging
from binascii import Error as BinasciiError
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, OperationalError, ProgrammingError, transaction
from django.utils.encoding import DjangoUnicodeDecodeError, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile
from apps.accounts.policies import can_use_local_password_reset
from apps.accounts.tokens import password_reset_token_generator
from apps.common.errors import DomainError

logger = logging.getLogger(__name__)


def register_user(*, email: str, password: str, display_name: str):
    """Register a new local user and profile."""
    User = get_user_model()
    normalized_email = User.objects.normalize_email(email)
    candidate_user = User(email=normalized_email, display_name=display_name)
    validate_password_strength(password=password, user=candidate_user, field="password")

    if User.objects.filter(email__iexact=normalized_email).exists():
        raise DomainError(
            code="email_already_registered",
            detail="A user with this email already exists.",
            field="email",
            status_code=HTTPStatus.CONFLICT,
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                display_name=display_name,
            )
            UserProfile.objects.create(user=user)
    except IntegrityError as exc:
        raise DomainError(
            code="email_already_registered",
            detail="A user with this email already exists.",
            field="email",
            status_code=HTTPStatus.CONFLICT,
        ) from exc

    return user


def get_or_create_profile(*, user) -> UserProfile:
    """Return a user's profile, creating it when missing."""
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def update_profile(*, user, timezone: str) -> UserProfile:
    """Update and return a user's profile."""
    profile = get_or_create_profile(user=user)
    profile.timezone = timezone
    profile.save(update_fields=["timezone"])
    return profile


def request_password_reset(*, email: str) -> None:
    """Accept a password reset request and send email when allowed."""
    User = get_user_model()
    normalized_email = User.objects.normalize_email(email)
    user = User.objects.filter(email__iexact=normalized_email).first()

    if not can_use_local_password_reset(user):
        return

    uid = urlsafe_base64_encode(str(user.pk).encode())
    token = password_reset_token_generator.make_token(user)
    try:
        send_mail(
            subject="Password reset",
            message=f"Use this uid and token to reset your password.\nuid: {uid}\ntoken: {token}",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("Password reset email could not be sent.", exc_info=True)


def confirm_password_reset(
    *,
    uid: str,
    token: str,
    new_password: str,
    new_password_confirm: str,
):
    """Confirm a password reset token and set the new password."""
    if new_password != new_password_confirm:
        raise DomainError(
            code="validation_error",
            detail="Passwords do not match.",
            field="new_password_confirm",
        )

    user = _user_from_uid(uid)
    if user is None or not can_use_local_password_reset(user):
        raise_password_reset_invalid()

    if not password_reset_token_generator.check_token(user, token):
        raise_password_reset_invalid()

    validate_password_strength(password=new_password, user=user, field="new_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_outstanding_tokens_for_user(user)
    return user


def change_password(
    *,
    user,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> None:
    """Change a user's password after checking the old password."""
    if new_password != new_password_confirm:
        raise DomainError(
            code="validation_error",
            detail="Passwords do not match.",
            field="new_password_confirm",
        )
    if not user.check_password(old_password):
        raise DomainError(
            code="invalid_password",
            detail="Old password is incorrect.",
            field="old_password",
        )

    validate_password_strength(password=new_password, user=user, field="new_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_outstanding_tokens_for_user(user)


def logout_refresh_token(*, refresh: str) -> None:
    """Blacklist one refresh token for logout."""
    try:
        RefreshToken(refresh).blacklist()
    except TokenError as exc:
        raise DomainError(
            code="token_not_valid",
            detail="Token is invalid or expired.",
            status_code=HTTPStatus.UNAUTHORIZED,
        ) from exc


def blacklist_outstanding_tokens_for_user(user) -> None:
    """Blacklist all outstanding refresh tokens for a user when possible."""
    try:
        for outstanding_token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding_token)
    except (OperationalError, ProgrammingError):
        return


def raise_password_reset_invalid() -> None:
    """Raise a standard invalid password reset error."""
    raise DomainError(
        code="password_reset_invalid",
        detail="Password reset token is invalid.",
        status_code=HTTPStatus.BAD_REQUEST,
    )


def validate_password_strength(*, password: str, user, field: str) -> None:
    """Validate password strength and raise a field-specific domain error."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise DomainError(
            code="validation_error",
            detail=password_validation_detail(exc),
            field=field,
        ) from exc


def password_validation_detail(error: DjangoValidationError) -> str:
    """Return a readable password validation error detail."""
    return " ".join(error.messages)


def _user_from_uid(uid: str):
    """Return a user decoded from a password reset uid."""
    User = get_user_model()
    try:
        decoded_uid = force_str(urlsafe_base64_decode(uid))
        user_id = User._meta.pk.to_python(decoded_uid)
    except (
        DjangoUnicodeDecodeError,
        DjangoValidationError,
        BinasciiError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()
