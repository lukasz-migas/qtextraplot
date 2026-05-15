"""Napari-aware floating colorbar widget."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from napari.layers import Image
from napari.utils.colormaps import Colormap
from qtpy.QtCore import QSignalBlocker
from qtpy.QtWidgets import QWidget

from qtextraplot.widgets import (
    ColorbarSizePreset,
    ColorbarStackItem,
    QtColorbarRangeSlider,
    QtFloatingColorbarWidget,
)


def _is_supported_image_layer(layer: ty.Any) -> ty.TypeGuard[Image]:
    return isinstance(layer, Image) and not bool(getattr(layer, "rgb", False))


def _preview_colormap(colormap: Colormap) -> Colormap:
    return colormap.copy(update={"low_color": None})


def _has_transparent_low_color(colormap: Colormap) -> bool:
    low_color = colormap.low_color
    if low_color is None:
        return False
    return float(low_color[-1]) == 0.0


class QtNapariImageColorbarWidget(QtFloatingColorbarWidget):
    """Floating colorbar widget synchronized with napari image layers."""

    def __init__(
        self,
        viewer: ty.Any,
        parent: QWidget | None = None,
        title: str = "Image colorbars",
        size_preset: ColorbarSizePreset = "medium",
    ) -> None:
        self.viewer = viewer
        self._base_colormaps: dict[Image, Colormap] = {}
        self._layer_widgets: dict[Image, QtColorbarRangeSlider] = {}
        self._widget_callbacks: dict[Image, ty.Callable[[tuple[float, float]], None]] = {}
        self._syncing = False
        super().__init__(parent=parent, title=title, size_preset=size_preset)
        self._connect_viewer_events()
        self.sync_layers()

    def widget_for_layer(self, layer: Image) -> QtColorbarRangeSlider | None:
        """Return the row widget for a napari image layer."""
        return self._layer_widgets.get(layer)

    def sync_layers(self) -> None:
        """Rebuild the colorbar rows from the current viewer layer list."""
        self._disconnect_layer_events()
        layers = [layer for layer in self.viewer.layers if _is_supported_image_layer(layer)]
        items = []
        for layer in layers:
            self._base_colormaps[layer] = _preview_colormap(layer.colormap)
            items.append(
                ColorbarStackItem(
                    label=layer.name,
                    data_range=tuple(layer.contrast_limits_range),
                    limits=tuple(layer.contrast_limits),
                    colorbar=self._base_colormaps[layer].colorbar,
                ),
            )

        self.set_items(items)
        self._layer_widgets = dict(zip(layers, self.stack.widgets, strict=True))
        for layer in layers:
            self._connect_layer_events(layer)
            self._apply_layer_threshold(layer, tuple(layer.contrast_limits), force=True)

    def closeEvent(self, event: ty.Any) -> None:
        """Disconnect napari events when the widget closes."""
        self._disconnect_viewer_events()
        self._disconnect_layer_events()
        super().closeEvent(event)

    def _connect_viewer_events(self) -> None:
        self.viewer.layers.events.inserted.connect(self._on_layers_changed)
        self.viewer.layers.events.removed.connect(self._on_layers_changed)
        self.viewer.layers.events.reordered.connect(self._on_layers_changed)

    def _disconnect_viewer_events(self) -> None:
        for emitter_name in ("inserted", "removed", "reordered"):
            with suppress(ValueError, RuntimeError):
                getattr(self.viewer.layers.events, emitter_name).disconnect(self._on_layers_changed)

    def _connect_layer_events(self, layer: Image) -> None:
        layer.events.colormap.connect(self._on_layer_colormap_change)
        layer.events.contrast_limits.connect(self._on_layer_limits_change)
        layer.events.contrast_limits_range.connect(self._on_layer_range_change)
        layer.events.name.connect(self._on_layer_name_change)

        callback = self._make_limits_callback(layer)
        self._widget_callbacks[layer] = callback
        self._layer_widgets[layer].limitsChanged.connect(callback)

    def _disconnect_layer_events(self) -> None:
        for layer, widget in list(self._layer_widgets.items()):
            with suppress(ValueError, RuntimeError):
                layer.events.colormap.disconnect(self._on_layer_colormap_change)
            with suppress(ValueError, RuntimeError):
                layer.events.contrast_limits.disconnect(self._on_layer_limits_change)
            with suppress(ValueError, RuntimeError):
                layer.events.contrast_limits_range.disconnect(self._on_layer_range_change)
            with suppress(ValueError, RuntimeError):
                layer.events.name.disconnect(self._on_layer_name_change)
            callback = self._widget_callbacks.get(layer)
            if callback is not None:
                with suppress(TypeError, RuntimeError):
                    widget.limitsChanged.disconnect(callback)
        self._layer_widgets.clear()
        self._widget_callbacks.clear()
        self._base_colormaps.clear()

    def _make_limits_callback(self, layer: Image) -> ty.Callable[[tuple[float, float]], None]:
        def _on_limits_changed(limits: tuple[float, float]) -> None:
            self._on_widget_limits_changed(layer, limits)

        return _on_limits_changed

    def _on_layers_changed(self, _event: ty.Any = None) -> None:
        self.sync_layers()

    def _on_layer_colormap_change(self, event: ty.Any) -> None:
        if self._syncing:
            return
        layer = event.source
        if layer not in self._layer_widgets:
            return
        self._base_colormaps[layer] = _preview_colormap(layer.colormap)
        self._layer_widgets[layer].set_colorbar(self._base_colormaps[layer].colorbar)
        self._apply_layer_threshold(layer, tuple(layer.contrast_limits), force=True)

    def _on_layer_limits_change(self, event: ty.Any) -> None:
        if self._syncing:
            return
        layer = event.source
        widget = self._layer_widgets.get(layer)
        if widget is None:
            return
        with QSignalBlocker(widget):
            widget.set_limits(tuple(layer.contrast_limits))
        self._apply_layer_threshold(layer, tuple(layer.contrast_limits))

    def _on_layer_range_change(self, event: ty.Any) -> None:
        if self._syncing:
            return
        layer = event.source
        widget = self._layer_widgets.get(layer)
        if widget is None:
            return
        with QSignalBlocker(widget):
            widget.set_data_range(tuple(layer.contrast_limits_range))
            widget.set_limits(tuple(layer.contrast_limits))
        self._apply_layer_threshold(layer, tuple(layer.contrast_limits))

    def _on_layer_name_change(self, event: ty.Any) -> None:
        layer = event.source
        widget = self._layer_widgets.get(layer)
        if widget is not None:
            widget.set_label(layer.name)

    def _on_widget_limits_changed(self, layer: Image, limits: tuple[float, float]) -> None:
        if self._syncing or layer not in self._layer_widgets:
            return
        previous = self._syncing
        self._syncing = True
        try:
            layer.contrast_limits = limits
            self._apply_layer_threshold(layer, limits)
        finally:
            self._syncing = previous

    def _apply_layer_threshold(self, layer: Image, limits: tuple[float, float], *, force: bool = False) -> None:
        data_min = float(layer.contrast_limits_range[0])
        active = float(limits[0]) > data_min
        if not force and _has_transparent_low_color(layer.colormap) == active:
            return
        base_colormap = self._base_colormaps.get(layer)
        if base_colormap is None:
            return
        low_color = [0.0, 0.0, 0.0, 0.0] if active else None
        previous = self._syncing
        self._syncing = True
        try:
            layer.colormap = base_colormap.copy(update={"low_color": low_color})
        finally:
            self._syncing = previous


__all__ = ["QtNapariImageColorbarWidget"]
