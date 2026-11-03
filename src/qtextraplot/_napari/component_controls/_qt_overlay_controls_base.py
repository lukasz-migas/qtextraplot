"""Base popup for controls that mirror fields of napari overlay models."""

from __future__ import annotations

import typing as ty

import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.components.overlays import Overlay
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QComboBox, QWidget

from qtextraplot._napari._enums import ViewerType


def _widget_accessors(widget: QWidget) -> tuple[ty.Any, ty.Callable[[], ty.Any], ty.Callable[[ty.Any], None]]:
    """Return the change signal, getter and setter used to sync ``widget``."""
    if isinstance(widget, QCheckBox):
        return widget.stateChanged, widget.isChecked, widget.setChecked
    if isinstance(widget, QComboBox):
        return (
            widget.currentIndexChanged,
            widget.currentData,
            lambda value: hp.set_combobox_current_index(widget, value),
        )
    if isinstance(widget, QColorSwatchEdit):
        return widget.color_changed, lambda: widget.color, widget.setColor
    # sliders, spin boxes and the optional font size / color widgets
    return widget.valueChanged, widget.value, widget.setValue


class QtOverlayControlsBase(QtFramelessPopup):
    """Popup whose widgets are kept in sync with napari overlay model fields."""

    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        self.viewer = viewer
        self._connections: list[tuple[ty.Any, ty.Callable]] = []

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)

    def _connect(self, emitter: ty.Any, callback: ty.Callable) -> None:
        """Connect a model event and remember it so it is disconnected on close."""
        emitter.connect(callback)
        self._connections.append((emitter, callback))

    def _bind(self, overlay: Overlay, field: str, widget: QWidget) -> QWidget:
        """Keep ``widget`` and ``overlay.<field>`` in sync in both directions."""
        signal, getter, setter = _widget_accessors(widget)

        def _to_model(*_args: ty.Any) -> None:
            setattr(overlay, field, getter())

        def _to_widget(_event: ty.Any = None) -> None:
            with hp.qt_signals_blocked(widget):
                setter(getattr(overlay, field))

        _to_widget()
        signal.connect(_to_model)
        self._connect(getattr(overlay.events, field), _to_widget)
        return widget

    def _bind_enabled(self, overlay: Overlay, *widgets: QWidget) -> None:
        """Disable ``widgets`` while the overlay is hidden."""

        def _on_visible_change(_event: ty.Any = None) -> None:
            hp.disable_widgets(*widgets, disabled=not overlay.visible)

        _on_visible_change()
        self._connect(overlay.events.visible, _on_visible_change)

    def close(self) -> None:
        """Disconnect model events when the popup closes."""
        for emitter, callback in self._connections:
            emitter.disconnect(callback)
        self._connections.clear()
        super().close()
