"""Unit tests for Git metadata policy validation."""

import pytest

from scripts.validate_commit_message import (
    contains_allowed_ticket,
    is_allowed_pull_request_target,
    main,
)


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(value="PROJECT-004 Add JWT user management", expected=True),
    dict(value="Add auth flow for PROJECT-004", expected=True),
    dict(value="PROJECT-011: Add release validation", expected=True),
    dict(value="HOTFIX-login-token-expiry", expected=True),
    dict(value="hotfix-login-token-expiry", expected=False),
    dict(value="Fix auth without ticket", expected=False),
    dict(value="PROJECT-auth malformed ticket", expected=False),
    dict(value="PROJECT-004x malformed ticket", expected=False),
    dict(value="HOTFIX- malformed hotfix", expected=False),
)
def test_contains_allowed_ticket(value, expected):
    """Verify commit and merge request titles must contain an allowed token."""
    assert contains_allowed_ticket(value) is expected


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(base_ref="release", head_ref="feature/PROJECT-011-release-policy", expected=True),
    dict(base_ref="release", head_ref="review/PROJECT-011", expected=True),
    dict(base_ref="master", head_ref="release", expected=True),
    dict(base_ref="master", head_ref="hotfix/HOTFIX-login-token-expiry", expected=True),
    dict(base_ref="master", head_ref="feature/PROJECT-011-release-policy", expected=False),
    dict(base_ref="main", head_ref="release", expected=False),
    dict(base_ref="develop", head_ref="feature/PROJECT-011-release-policy", expected=False),
)
def test_is_allowed_pull_request_target(base_ref, head_ref, expected):
    """Verify pull request target branch policy."""
    assert is_allowed_pull_request_target(base_ref=base_ref, head_ref=head_ref) is expected


@pytest.mark.unit
@pytest.mark.kwparametrize(
    dict(argv=["--value", "PROJECT-011 Add policy"], expected=0),
    dict(argv=["--kind", "merge request", "--value", "Invalid title"], expected=1),
    dict(
        argv=[
            "--mode",
            "pull-request-target",
            "--base-ref",
            "release",
            "--head-ref",
            "feature/PROJECT-011-release-policy",
        ],
        expected=0,
    ),
    dict(
        argv=[
            "--mode",
            "pull-request-target",
            "--base-ref",
            "master",
            "--head-ref",
            "feature/PROJECT-011-release-policy",
        ],
        expected=1,
    ),
)
def test_main_returns_expected_exit_code(argv, expected):
    """Verify the validator CLI returns the expected exit code."""
    assert main(argv) == expected
