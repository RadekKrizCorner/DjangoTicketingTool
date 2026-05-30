"""Account policy helpers."""

from typing import Any


def can_use_local_password_reset(user: Any) -> bool:
    """Return whether a user can use local password reset."""
    return bool(user and user.is_active and user.has_usable_password())
