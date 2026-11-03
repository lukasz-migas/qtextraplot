"""Font size control for napari overlays whose font size can be automatic."""

from __future__ import annotations

import typing as ty

import qtextra.helpers as hp
from qtpy.QtCore import Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QWidget


def default_font_size() -> float:
    """Return the font size napari uses for overlays with ``font_size=None``."""
    from napari.settings import get_settings

    return float(get_settings().appearance.font_size)


class QtFontSizeWidget(QWidget):
    """Font size slider with an *Auto* toggle.

    The value is ``None`` when *Auto* is checked, which tells napari to follow the
    application font size setting.
    """

    valueChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        value: float | None = None,
        min_value: float = 4,
        max_value: float = 32,
        func: ty.Callable[[float | None], None] | None = None,
    ):
        super().__init__(parent)
        self.auto_checkbox = hp.make_checkbox(
            self,
            "Auto",
            "Follow the application font size.",
            value=value is None,
            func=self._on_auto_change,
        )
        self.slider = hp.make_double_slider_with_text(
            self,
            min_value,
            max_value,
            step_size=1,
            value=default_font_size() if value is None else value,
            func=self._on_slider_change,
        )
        self.slider.setEnabled(value is not None)
        hp.make_h_layout(self.auto_checkbox, self.slider, stretch_id=(1,), spacing=2, margin=0, parent=self)
        if func is not None:
            self.valueChanged.connect(func)

    def value(self) -> float | None:
        """Return the font size, or ``None`` when automatic."""
        return None if self.auto_checkbox.isChecked() else self.slider.value()

    def setValue(self, value: float | None) -> None:
        """Set the font size, emitting ``valueChanged`` if it changed."""
        previous = self.value()
        with hp.qt_signals_blocked(self.auto_checkbox, self.slider):
            self.auto_checkbox.setChecked(value is None)
            self.slider.setValue(default_font_size() if value is None else value)
            self.slider.setEnabled(value is not None)
        if self.value() != previous:
            self.valueChanged.emit(self.value())

    def _on_auto_change(self) -> None:
        auto = self.auto_checkbox.isChecked()
        self.slider.setEnabled(not auto)
        if auto:
            with hp.qt_signals_blocked(self.slider):
                self.slider.setValue(default_font_size())
        self.valueChanged.emit(self.value())

    def _on_slider_change(self) -> None:
        self.valueChanged.emit(self.value())
