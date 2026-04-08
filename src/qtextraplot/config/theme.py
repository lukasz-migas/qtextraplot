"""Themes configuration file."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.color import get_random_hex_color
from psygnal._evented_model import EventedModel
from pydantic import PrivateAttr
from pydantic_extra_types.color import Color
from qtextra.config import THEMES
from qtextra.config.config import ConfigBase
from qtpy.QtCore import Signal

DARK_THEME = {
    "canvas": "black",
    "line": "white",
    "scatter": "white",
    "highlight": "yellow",
    "axis": "white",
    "gridlines": "white",
    "label": "lightgray",
}
LIGHT_THEME = {
    "canvas": "white",
    "line": "black",
    "scatter": "black",
    "highlight": "yellow",
    "axis": "black",
    "gridlines": "black",
    "label": "black",
}


class CanvasTheme(EventedModel):
    """Plot theme model."""

    canvas: Color
    line: Color
    scatter: Color
    highlight: Color
    axis: Color
    gridlines: Color
    label: Color
    _canvas_backup: Color | None = PrivateAttr(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._canvas_backup = self.canvas

    def as_array(self, name: str) -> np.ndarray:
        """Return color array."""
        return np.asarray(getattr(self, name))


class CanvasThemes(ConfigBase):
    """Plot theme class."""

    # event emitted whenever a theme is changed
    evt_theme_changed = Signal()

    def __init__(self):
        super().__init__(None)
        self.themes = {}
        self._theme = "light"
        self._integrate_canvas: bool = False

        self.add_theme("dark", CanvasTheme(**DARK_THEME))
        self.add_theme("light", CanvasTheme(**LIGHT_THEME))

        for theme in self.themes.values():
            theme.events.connect(self._on_theme_model_changed)

    @property
    def integrate_canvas(self):
        """Integrate canvas with background color."""
        return self._integrate_canvas

    @integrate_canvas.setter
    def integrate_canvas(self, value):
        self._integrate_canvas = value
        background = THEMES.active.background if value else self.active._canvas_backup
        self.active.canvas = background

    def _on_theme_model_changed(self, _event=None) -> None:
        """Forward any field-level change on the active theme model to listeners."""
        self.evt_theme_changed.emit()

    def add_theme(self, name: str, theme_data: ty.Union[CanvasTheme, ty.Dict[str, str]]):
        """Add theme."""
        if isinstance(theme_data, CanvasTheme):
            self.themes[name] = theme_data
        else:
            self.themes[name] = CanvasTheme(**theme_data)

    def available_themes(self) -> ty.Tuple[str, ...]:
        """Get list of available themes."""
        return tuple(self.themes)

    @property
    def active(self) -> CanvasTheme:
        """Return active theme."""
        return self.themes[self.theme]

    @property
    def theme(self) -> str:
        """Return theme name."""
        return self._theme

    @theme.setter
    def theme(self, value: str):
        if self._theme == value:
            return
        if value not in self.themes:
            return
        self._theme = value
        self.integrate_canvas = self._integrate_canvas
        self.evt_theme_changed.emit()

    def as_array(self, name: str) -> np.ndarray:
        """Return color array."""
        from napari.utils.colormaps.standardize_color import transform_color

        color: Color = getattr(self.active, name)
        return transform_color(color.as_hex())[0]

    def as_hex(self, name: str) -> str:
        """Return color as hex."""
        color: Color = getattr(self.active, name)
        return color.as_hex()

    def check_color(self, color: ty.Any) -> ty.Any:
        """Check whether color clashes with the background color."""
        from napari.utils.colormaps.standardize_color import transform_color

        background = transform_color(self.active.canvas.as_hex())[0]
        color = transform_color(color)[0]
        # check whether color is too similar to background
        if np.linalg.norm(color - background) < 0.3:  # arbitrary threshold; colors are normalized 0-1
            return get_random_hex_color()
        return color


CANVAS: CanvasThemes = CanvasThemes()
