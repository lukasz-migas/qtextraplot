"""Color control for napari overlays whose color can be automatic."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QWidget


class QtOptionalColorWidget(QWidget):
    """Color swatch with an *Auto* toggle.

    The value is ``None`` when *Auto* is checked, which tells napari to pick the color
    itself (e.g. contrasting with the canvas background).
    """

    valueChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        value: ty.Any = None,
        fallback: ty.Any = "white",
        auto_text: str = "Auto",
        auto_tooltip: str = "Let napari choose the color.",
        func: ty.Callable[[np.ndarray | None], None] | None = None,
    ):
        super().__init__(parent)
        self.auto_checkbox = hp.make_checkbox(self, auto_text, auto_tooltip, value=value is None)
        self.color_swatch = QColorSwatchEdit(self, initial_color=fallback if value is None else value)
        self.color_swatch.setEnabled(value is not None)
        self.auto_checkbox.stateChanged.connect(self._on_auto_change)
        self.color_swatch.color_changed.connect(self._on_color_change)
        hp.make_h_layout(self.auto_checkbox, self.color_swatch, stretch_id=(1,), spacing=2, margin=0, parent=self)
        if func is not None:
            self.valueChanged.connect(func)

    def value(self) -> np.ndarray | None:
        """Return the color, or ``None`` when automatic."""
        return None if self.auto_checkbox.isChecked() else self.color_swatch.color

    def setValue(self, value: ty.Any) -> None:
        """Set the color without emitting ``valueChanged``."""
        with hp.qt_signals_blocked(self.auto_checkbox, self.color_swatch):
            self.auto_checkbox.setChecked(value is None)
            if value is not None:
                self.color_swatch.setColor(value)
            self.color_swatch.setEnabled(value is not None)

    def _on_auto_change(self) -> None:
        self.color_swatch.setEnabled(not self.auto_checkbox.isChecked())
        self.valueChanged.emit(self.value())

    def _on_color_change(self, _color: np.ndarray) -> None:
        if not self.auto_checkbox.isChecked():
            self.valueChanged.emit(self.value())
