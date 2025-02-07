"""Themes configuration file."""

import typing as ty

import numpy as np
from psygnal._evented_model import EventedModel
from pydantic import PrivateAttr
from pydantic.color import Color
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
    _canvas_backup: ty.Optional[Color] = PrivateAttr(None)

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
            theme.events.connect(lambda _: self.evt_theme_changed.emit())

    @property
    def integrate_canvas(self):
        """Integrate canvas with background color."""
        return self._integrate_canvas

    @integrate_canvas.setter
    def integrate_canvas(self, value):
        self._integrate_canvas = value
        background = THEMES.active.background if value else self.active._canvas_backup
        self.active.canvas = background

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


CANVAS: CanvasThemes = CanvasThemes()
