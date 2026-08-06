"""Layer name overlay controls."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit  # type: ignore[import-untyped]
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QWidget

from qtextraplot._napari._constants import POSITION_TRANSLATIONS

_OVERLAY_PROPERTIES = ("visible", "color", "position", "font_size", "opacity")
_DEFAULT_COLOR = (0.5, 0.5, 0.5, 1.0)
_DEFAULT_POSITION = next(iter(POSITION_TRANSLATIONS))


class QtLayerNameOverlayControls(QtFramelessPopup):
    """Popup to control the name overlays of all napari layers."""

    def __init__(self, viewer: ty.Any, parent: QWidget | None = None) -> None:
        self.viewer = viewer
        self._connected_overlays: list[ty.Any] = []

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("layer_name_overlay")
        self.setMouseTracking(True)

        self.viewer.layers.events.inserted.connect(self._on_layer_collection_change)
        self.viewer.layers.events.removed.connect(self._on_layer_collection_change)
        self.viewer.layers.events.changed.connect(self._on_layer_collection_change)
        self._refresh_overlay_connections()

    def _layer_iter(self) -> ty.Iterator[ty.Any]:
        """Yield layers that expose a name overlay."""
        return (layer for layer in self.viewer.layers if hasattr(layer, "name_overlay"))

    def _overlays(self) -> list[ty.Any]:
        """Return the currently available layer name overlays."""
        return [layer.name_overlay for layer in self._layer_iter()]

    def _get_common_value(self, attribute: str, default: ty.Any) -> ty.Any:
        """Return the first available overlay value or a safe default."""
        overlay = next(iter(self._overlays()), None)
        if overlay is None:
            return default
        value = getattr(overlay, attribute, default)
        if value is None:
            return default
        return value

    def _set_overlay_value(self, attribute: str, value: ty.Any) -> None:
        """Set an attribute on every available layer name overlay."""
        for overlay in self._overlays():
            setattr(overlay, attribute, value)

    def _connect_overlay(self, overlay: ty.Any) -> None:
        """Connect model events for one overlay."""
        for attribute in _OVERLAY_PROPERTIES:
            with suppress(AttributeError):
                getattr(overlay.events, attribute).connect(self._on_overlay_change)

    def _disconnect_overlay(self, overlay: ty.Any) -> None:
        """Disconnect model events for one overlay."""
        for attribute in _OVERLAY_PROPERTIES:
            with suppress(AttributeError, TypeError, ValueError):
                getattr(overlay.events, attribute).disconnect(self._on_overlay_change)

    def _refresh_overlay_connections(self, _event: ty.Any = None) -> None:
        """Refresh model event connections after the layer collection changes."""
        for overlay in self._connected_overlays:
            self._disconnect_overlay(overlay)
        self._connected_overlays = self._overlays()
        for overlay in self._connected_overlays:
            self._connect_overlay(overlay)
        self._sync_controls()

    def _on_layer_collection_change(self, _event: ty.Any = None) -> None:
        """Refresh controls when layers are added, removed, or replaced."""
        self._refresh_overlay_connections()

    def _on_overlay_change(self, _event: ty.Any = None) -> None:
        """Refresh controls after an overlay model value changes."""
        self._sync_controls()

    def _sync_controls(self) -> None:
        """Update widgets from the first available layer name overlay."""
        has_overlay = bool(self._connected_overlays)
        with hp.qt_signals_blocked(self.visible_checkbox):
            self.visible_checkbox.setChecked(self._get_common_value("visible", False))
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self._get_common_value("color", _DEFAULT_COLOR))
        with hp.qt_signals_blocked(self.position_combobox):
            hp.set_combobox_current_index(
                self.position_combobox,
                self._get_common_value("position", _DEFAULT_POSITION),
            )
        with hp.qt_signals_blocked(self.font_size_spinbox):
            self.font_size_spinbox.setValue(self._get_common_value("font_size", 10.0))
        with hp.qt_signals_blocked(self.opacity_spinbox):
            self.opacity_spinbox.setValue(self._get_common_value("opacity", 1.0))
        hp.disable_widgets(
            self.visible_checkbox,
            self.color_swatch,
            self.position_combobox,
            self.font_size_spinbox,
            self.opacity_spinbox,
            disabled=not has_overlay,
        )

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Create the layer name overlay controls panel."""
        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide layer names",
            value=self._get_common_value("visible", False),
            func=self.on_change_visible,
        )
        self.color_swatch = QColorSwatchEdit(
            self,
            initial_color=self._get_common_value("color", _DEFAULT_COLOR),
            tooltip="Set the layer name color.",
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.position_combobox = hp.make_combobox(
            self,
            data=POSITION_TRANSLATIONS,
            value=self._get_common_value("position", _DEFAULT_POSITION),
            func=self.on_change_position,
        )
        self.font_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            n_decimals=1,
            value=self._get_common_value("font_size", 10.0),
            func=self.on_change_font_size,
        )
        self.opacity_spinbox = hp.make_double_slider_with_text(
            self,
            0,
            1,
            step_size=0.01,
            n_decimals=2,
            value=self._get_common_value("opacity", 1.0),
            func=self.on_change_opacity,
        )

        layout = hp.make_form_layout(parent=self, margin=(6, 6, 6, 6))
        layout.addRow(self._make_move_handle("Layer name overlay controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.addRow(hp.make_label(self, "Opacity"), self.opacity_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self) -> None:
        """Update visibility on every layer name overlay."""
        self._set_overlay_value("visible", self.visible_checkbox.isChecked())

    def on_change_color(self, color: np.ndarray) -> None:
        """Update color on every layer name overlay."""
        self._set_overlay_value("color", color)

    def on_change_position(self) -> None:
        """Update position on every layer name overlay."""
        self._set_overlay_value("position", self.position_combobox.currentData())

    def on_change_font_size(self) -> None:
        """Update font size on every layer name overlay."""
        self._set_overlay_value("font_size", self.font_size_spinbox.value())

    def on_change_opacity(self) -> None:
        """Update opacity on every layer name overlay."""
        self._set_overlay_value("opacity", self.opacity_spinbox.value())

    def close(self) -> bool:
        """Disconnect model events when the popup closes."""
        self.viewer.layers.events.inserted.disconnect(self._on_layer_collection_change)
        self.viewer.layers.events.removed.disconnect(self._on_layer_collection_change)
        self.viewer.layers.events.changed.disconnect(self._on_layer_collection_change)
        for overlay in self._connected_overlays:
            self._disconnect_overlay(overlay)
        self._connected_overlays.clear()
        return super().close()
