"""Unit tests for declared runtime and dependency versions."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_runtime_targets_314() -> None:
    """Verify Docker, package metadata, Ruff, and CI target Python 3.14."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ci_workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    git_policy_workflow = (
        REPO_ROOT / ".github/workflows/git-policy.yml"
    ).read_text(encoding="utf-8")

    assert "FROM python:3.14-slim AS base" in dockerfile
    assert 'requires-python = ">=3.14,<3.15"' in pyproject
    assert 'target-version = "py314"' in pyproject
    assert 'python-version: "3.14"' in ci_workflow
    assert 'python-version: "3.14"' in git_policy_workflow
    assert "python:3.12-slim" not in dockerfile
    assert 'python-version: "3.12"' not in ci_workflow
    assert 'python-version: "3.12"' not in git_policy_workflow


def test_django_stack_targets_django_6() -> None:
    """Verify backend package constraints target Django 6 compatible versions."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    expected_constraints = [
        '"django>=6.0,<6.1"',
        '"django-filter>=25.2,<26.0"',
        '"djangorestframework>=3.17,<4.0"',
        '"djangorestframework-simplejwt>=5.5,<6.0"',
        '"drf-spectacular>=0.29,<1.0"',
        '"gunicorn>=26.0,<27.0"',
        '"psycopg[binary]>=3.3,<4.0"',
        '"pytest>=9.0,<10.0"',
        '"pytest-cov>=7.1,<8.0"',
        '"pytest-django>=4.12,<5.0"',
        '"ruff>=0.15,<1.0"',
    ]
    retired_constraints = [
        '"django>=5.2,<5.3"',
        '"django-filter>=24.3,<25.0"',
        '"djangorestframework>=3.15,<4.0"',
        '"gunicorn>=22.0,<23.0"',
        '"pytest>=8.3,<9.0"',
        '"ruff>=0.6,<1.0"',
    ]

    for constraint in expected_constraints:
        assert constraint in pyproject
    for constraint in retired_constraints:
        assert constraint not in pyproject


def test_postgres_and_redis_runtime_images_are_current() -> None:
    """Verify local, release, and CI services use PostgreSQL 18 and Redis 8."""
    local_compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    release_compose = (REPO_ROOT / "docker-compose.release.yml").read_text(
        encoding="utf-8"
    )
    ci_workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for content in (local_compose, release_compose, ci_workflow):
        assert "postgres:18-alpine" in content
        assert "redis:8-alpine" in content
        assert "postgres:16-alpine" not in content
        assert "redis:7-alpine" not in content
