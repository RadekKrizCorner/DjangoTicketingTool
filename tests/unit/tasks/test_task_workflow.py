"""Unit tests for task workflow rules."""

import pytest


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(current="new", target="accepted", allowed=True),
    dict(current="new", target="in_progress", allowed=False),
    dict(current="new", target="cancelled", allowed=True),
    dict(current="accepted", target="in_progress", allowed=True),
    dict(current="accepted", target="on_hold", allowed=True),
    dict(current="accepted", target="completed", allowed=False),
    dict(current="in_progress", target="on_hold", allowed=True),
    dict(current="in_progress", target="completed", allowed=True),
    dict(current="on_hold", target="in_progress", allowed=True),
    dict(current="completed", target="accepted", allowed=True),
    dict(current="cancelled", target="accepted", allowed=True),
)
def test_task_transition_matrix(current, target, allowed):
    """Verify task workflow transition matrix."""
    from apps.tasks.workflow import is_transition_allowed

    assert is_transition_allowed(current=current, target=target) is allowed
