"""Unit tests for project permission policies."""

import pytest


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(role="owner", action="read", expected=True),
    dict(role="owner", action="manage_members", expected=True),
    dict(role="owner", action="delete", expected=True),
    dict(role="owner", action="schedule", expected=True),
    dict(role="owner", action="transfer", expected=True),
    dict(role="owner", action="audit", expected=True),
    dict(role="owner", action="close", expected=True),
    dict(role="owner", action="reopen", expected=True),
    dict(role="manager", action="read", expected=True),
    dict(role="manager", action="manage_members", expected=False),
    dict(role="manager", action="delete", expected=False),
    dict(role="manager", action="schedule", expected=False),
    dict(role="manager", action="transfer", expected=False),
    dict(role="manager", action="audit", expected=False),
    dict(role="manager", action="close", expected=False),
    dict(role="manager", action="reopen", expected=False),
    dict(role="member", action="read", expected=True),
    dict(role="member", action="manage_members", expected=False),
    dict(role="member", action="delete", expected=False),
    dict(role="member", action="schedule", expected=False),
    dict(role="member", action="transfer", expected=False),
    dict(role="member", action="audit", expected=False),
    dict(role="member", action="close", expected=False),
    dict(role="member", action="reopen", expected=False),
    dict(role="viewer", action="read", expected=True),
    dict(role="viewer", action="manage_members", expected=False),
    dict(role="viewer", action="delete", expected=False),
    dict(role="viewer", action="schedule", expected=False),
    dict(role="viewer", action="transfer", expected=False),
    dict(role="viewer", action="audit", expected=False),
    dict(role="viewer", action="close", expected=False),
    dict(role="viewer", action="reopen", expected=False),
)
def test_role_action_matrix(role, action, expected):
    """Verify finite project role permissions."""
    from apps.projects.policies import role_allows_action

    assert role_allows_action(role=role, action=action) is expected


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(action="schedule", expected=True),
    dict(action="close", expected=True),
    dict(action="reopen", expected=True),
    dict(action="manage_members", expected=False),
    dict(action="delete", expected=False),
    dict(action="transfer", expected=False),
    dict(action="audit", expected=False),
)
def test_staff_lifecycle_override_matrix(action, expected):
    """Verify staff override is limited to lifecycle scheduling actions."""
    from apps.projects.policies import staff_allows_action

    assert staff_allows_action(action=action) is expected
