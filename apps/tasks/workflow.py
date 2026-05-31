"""Task workflow transition rules."""

ALLOWED_TRANSITIONS = {
    "new": {"accepted", "cancelled"},
    "accepted": {"in_progress", "on_hold", "cancelled"},
    "in_progress": {"on_hold", "completed", "cancelled"},
    "on_hold": {"in_progress", "cancelled"},
    "completed": {"accepted"},
    "cancelled": {"accepted"},
}


def is_transition_allowed(*, current: str, target: str) -> bool:
    """Return whether a task status transition is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current, set())
