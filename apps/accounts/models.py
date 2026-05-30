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
