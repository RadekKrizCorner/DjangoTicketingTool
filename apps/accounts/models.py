"""Account models."""

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Represent an email-based application user."""

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        """Configure user model metadata and constraints."""

        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_uniq",
            )
        ]
        ordering = ["email", "id"]

    def __str__(self) -> str:
        """Return the user's email address."""
        return self.email

    def save(self, *args, **kwargs) -> None:
        """Normalize the email address before saving the user."""
        self.email = type(self).objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        """Return the user's display name."""
        return self.display_name

    def get_short_name(self) -> str:
        """Return the user's display name."""
        return self.display_name


class UserProfile(models.Model):
    """Store user profile preferences."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    timezone = models.CharField(max_length=64, default="UTC")

    class Meta:
        """Configure user profile metadata."""

        ordering = ["user_id"]

    def __str__(self) -> str:
        """Return a readable profile label."""
        return f"Profile for {self.user_id}"


class ExternalIdentity(models.Model):
    """Store a future SSO identity linked to a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="external_identities",
    )
    provider = models.CharField(max_length=100)
    provider_subject = models.CharField(max_length=255)
    email_at_link_time = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configure external identity metadata and constraints."""

        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subject"],
                name="accounts_external_identity_provider_subject_uniq",
            )
        ]
        ordering = ["provider", "provider_subject", "id"]

    def __str__(self) -> str:
        """Return a readable external identity label."""
        return f"{self.provider}:{self.provider_subject}"


class PersonalAccessToken(models.Model):
    """Store a hashed personal API token for scripts and API clients."""

    SCOPE_FULL_ACCESS = "full_access"
    SCOPE_READ_ONLY = "read_only"
    READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_access_tokens",
    )
    name = models.CharField(max_length=100)
    token_prefix = models.CharField(max_length=20, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Configure personal access token metadata."""

        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="accounts_pat_user_created_idx"),
            models.Index(fields=["revoked_at", "expires_at"], name="accounts_pat_status_idx"),
        ]

    def __str__(self) -> str:
        """Return a readable personal access token label."""
        return f"{self.name} ({self.user_id})"

    def is_expired(self) -> bool:
        """Return whether the token is past its expiry timestamp."""
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def is_revoked(self) -> bool:
        """Return whether the token has been revoked."""
        return self.revoked_at is not None

    def is_usable(self) -> bool:
        """Return whether the token can authenticate requests."""
        return bool(self.user.is_active and not self.is_revoked() and not self.is_expired())

    def allows_method(self, method: str) -> bool:
        """Return whether token scopes allow an HTTP method."""
        if self.SCOPE_FULL_ACCESS in self.scopes:
            return True
        if self.SCOPE_READ_ONLY in self.scopes:
            return method.upper() in self.READ_ONLY_METHODS
        return False
