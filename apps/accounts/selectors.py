"""Account query selectors."""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.accounts.models import PersonalAccessToken


def active_users() -> QuerySet:
    """Return active users ordered consistently."""
    User = get_user_model()
    return User.objects.filter(is_active=True).order_by("email", "id")


def search_active_users(term: str | None = None) -> QuerySet:
    """Return active users matching an optional search term."""
    users = active_users()
    normalized_term = (term or "").strip()
    if not normalized_term:
        return users
    return users.filter(
        Q(email__icontains=normalized_term) | Q(display_name__icontains=normalized_term)
    )


def personal_access_tokens_for_user(*, user) -> QuerySet[PersonalAccessToken]:
    """Return personal access tokens owned by a user."""
    return PersonalAccessToken.objects.filter(user=user).order_by("-created_at", "-id")
