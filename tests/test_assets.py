"""Tests for qtextraplot asset registration and stylesheet overrides."""

from __future__ import annotations

import pytest
from qtextra.config import THEMES

import qtextraplot.assets  # noqa: F401  # Register qtextraplot and napari styles.


def _rule_body(stylesheet: str, selector_index: int) -> str:
    opening_brace = stylesheet.index("{", selector_index)
    closing_brace = stylesheet.index("}", opening_brace)
    return stylesheet[opening_brace + 1 : closing_brace]


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_checked_checkbox_background_override_is_applied_last(theme_name: str) -> None:
    """The qtextraplot reset should follow napari's global checked fill."""
    stylesheet = THEMES.get_theme_stylesheet(theme_name)
    napari_selector = "QCheckBox::indicator:checked {"
    override_selector = 'QCheckBox::indicator:checked,\nQWidget[emphasized="true"] QCheckBox::indicator:checked {'

    napari_index = stylesheet.index(napari_selector)
    override_index = stylesheet.rindex(override_selector)

    assert f"background-color: {THEMES.get_theme_color('current', theme_name)};" in _rule_body(
        stylesheet,
        napari_index,
    )
    assert "background-color: transparent;" in _rule_body(stylesheet, override_index)
    assert override_index > napari_index
