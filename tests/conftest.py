"""Pytest configuration for the project test suite."""

import pytest


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    """Store uploaded test files under a per-test temporary media root."""
    settings.MEDIA_ROOT = tmp_path / "media"
