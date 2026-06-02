"""Tests for release environment documentation."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def compose_environment_names(path: Path) -> set[str]:
    """Return external Compose environment variable names used by a file."""
    pattern = re.compile(r"\$\{(?P<name>[A-Z0-9_]+)(?::[-?][^}]*)?\}")
    return set(pattern.findall(path.read_text()))


def env_template_names() -> set[str]:
    """Return variable names defined by the release env template."""
    env_template = REPO_ROOT / ".env_template"
    pattern = re.compile(r"^(?P<name>[A-Z0-9_]+)=", re.MULTILINE)
    return set(pattern.findall(env_template.read_text()))


@pytest.mark.kwparametrize(
    {"compose_file": "docker-compose.release.yml"},
    {"compose_file": "docker-compose.release.storage.yml"},
    {"compose_file": "docker-compose.release.monitoring.yml"},
)
def test_env_template_covers_release_compose_variables(compose_file):
    """Verify the env template documents every release Compose variable."""
    compose_names = compose_environment_names(REPO_ROOT / compose_file)

    assert compose_names <= env_template_names()


def test_release_gateway_blocks_internal_metrics_endpoint():
    """Verify public release traffic cannot reach the internal metrics endpoint."""
    nginx_config = (REPO_ROOT / "deploy/release/nginx.conf").read_text()

    assert "location = /internal/metrics" in nginx_config
    assert "location ^~ /internal/" in nginx_config
    assert "return 404;" in nginx_config


@pytest.mark.kwparametrize(
    {
        "path": "docs/reviews/product-specification-review.md",
        "title": "Product Specification Review",
    },
    {
        "path": "docs/superpowers/specs/2026-05-30-project-management-backend-design.md",
        "title": "Project Management Backend Design",
    },
    {
        "path": "docs/superpowers/plans/2026-05-30-project-management-backend-implementation.md",
        "title": "Project Management Backend Implementation Plan",
    },
)
def test_internal_docs_pages_are_removed_from_current_tree(path, title):
    """Verify internal planning pages are not shipped in current docs."""
    mkdocs_text = (REPO_ROOT / "mkdocs.yml").read_text()

    assert not (REPO_ROOT / path).exists()
    assert path.removeprefix("docs/") not in mkdocs_text
    assert title not in mkdocs_text
