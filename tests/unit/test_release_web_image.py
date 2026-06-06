"""Unit tests for the release web image configuration."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_web_image_builds_frontend_ui() -> None:
    """Verify the web image builds the React UI for release serving."""
    dockerfile = (REPO_ROOT / "Dockerfile.web").read_text(encoding="utf-8")

    assert "FROM node:" in dockerfile
    assert "VITE_BASE_PATH=/ui/" in dockerfile
    assert "VITE_DEMO_MODE=live" in dockerfile
    assert "COPY --from=frontend-build /frontend/dist /usr/share/nginx/html/ui" in dockerfile


def test_release_nginx_serves_ui_before_api_proxy() -> None:
    """Verify Nginx serves the UI route before proxying to Django."""
    nginx_config = (REPO_ROOT / "deploy/release/nginx.conf").read_text(encoding="utf-8")

    assert "location = /ui" in nginx_config
    assert "location /ui/" in nginx_config
    assert "try_files $uri $uri/ /ui/index.html;" in nginx_config
    assert nginx_config.index("    location /ui/ {") < nginx_config.index("    location / {")
