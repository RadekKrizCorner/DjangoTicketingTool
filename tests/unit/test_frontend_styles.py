"""Unit tests for frontend stylesheet contracts."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _css_rule(css: str, selector: str) -> str:
    """Return a simple CSS rule body for a selector."""
    marker = f"{selector} {{"
    start = css.index(marker) + len(marker)
    end = css.index("}", start)
    return css[start:end]


def test_project_list_layout_uses_available_content_width() -> None:
    """Verify project list layout does not cap table width."""
    css = (REPO_ROOT / "frontend/src/index.css").read_text(encoding="utf-8")
    rule = _css_rule(css, ".projects-list-layout")

    assert "max-width" not in rule


def test_mobile_styles_convert_tables_to_cards() -> None:
    """Verify mobile tables use card layout instead of horizontal scrolling."""
    css = (REPO_ROOT / "frontend/src/index.css").read_text(encoding="utf-8")

    assert "@media (max-width: 680px)" in css
    assert ".data-table.responsive-cards" in css
    assert "content: attr(data-label)" in css
    assert ".table-wrap.responsive-table" in css


def test_mobile_styles_raise_touch_targets_and_hide_demo_alert() -> None:
    """Verify mobile controls are finger-sized and demo alert is hidden."""
    css = (REPO_ROOT / "frontend/src/index.css").read_text(encoding="utf-8")

    assert ".mobile-search-trigger" in css
    assert ".button,\n  .icon-button,\n  .tab,\n  .input,\n  .select" in css
    assert "min-height: 44px" in css
    assert ".alert.mobile-hidden" in css
    assert "display: none" in css


def test_mobile_styles_improve_task_detail_context() -> None:
    """Verify mobile task detail keeps selected task context visible."""
    css = (REPO_ROOT / "frontend/src/index.css").read_text(encoding="utf-8")

    assert ".mobile-task-detail-summary" in css
    assert ".task-detail-anchor" in css
    assert ".task-board" in css
    assert "scroll-snap-type: x proximity" in css
