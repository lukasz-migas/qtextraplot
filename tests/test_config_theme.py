"""Tests for the canvas theme configuration."""

from __future__ import annotations

import numpy as np
import pytest

from qtextraplot.config.theme import CANVAS, CanvasTheme, CanvasThemes, DARK_THEME, LIGHT_THEME


class TestCanvasTheme:
    def test_dark_theme_canvas_color(self):
        theme = CanvasTheme(**DARK_THEME)
        assert theme.canvas is not None

    def test_light_theme_canvas_color(self):
        theme = CanvasTheme(**LIGHT_THEME)
        assert theme.canvas is not None

    def test_as_array_returns_numpy(self):
        theme = CanvasTheme(**LIGHT_THEME)
        arr = theme.as_array("canvas")
        assert isinstance(arr, np.ndarray)


class TestCanvasThemes:
    def test_default_theme_is_light(self):
        themes = CanvasThemes()
        assert themes.theme == "light"

    def test_active_returns_canvas_theme(self):
        themes = CanvasThemes()
        assert isinstance(themes.active, CanvasTheme)

    def test_available_themes_contains_dark_and_light(self):
        themes = CanvasThemes()
        available = themes.available_themes()
        assert "dark" in available
        assert "light" in available

    def test_switch_theme(self, qtbot):
        themes = CanvasThemes()
        themes.theme = "dark"
        assert themes.theme == "dark"
        themes.theme = "light"
        assert themes.theme == "light"

    def test_switch_theme_emits_signal(self, qtbot):
        themes = CanvasThemes()
        themes.theme = "light"
        with qtbot.waitSignal(themes.evt_theme_changed, timeout=1000):
            themes.theme = "dark"

    def test_invalid_theme_ignored(self):
        themes = CanvasThemes()
        original = themes.theme
        themes.theme = "nonexistent"
        assert themes.theme == original

    def test_as_hex_returns_string(self):
        themes = CanvasThemes()
        hex_color = themes.as_hex("canvas")
        assert isinstance(hex_color, str)
        assert hex_color.startswith("#")

    def test_add_custom_theme(self):
        themes = CanvasThemes()
        custom = {
            "canvas": "blue",
            "line": "white",
            "scatter": "white",
            "highlight": "yellow",
            "axis": "white",
            "gridlines": "white",
            "label": "white",
        }
        themes.add_theme("custom_blue", custom)
        assert "custom_blue" in themes.available_themes()


class TestGlobalCanvas:
    """Smoke tests for the module-level CANVAS singleton."""

    def test_canvas_is_canvas_themes(self):
        assert isinstance(CANVAS, CanvasThemes)

    def test_canvas_has_active(self):
        assert CANVAS.active is not None
