"""Line viewer model with legend overlay support."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari.layers import Points
from napari.layers.base import Layer
from napari_plot.layers import Centroids, Line, Scatter
from napari_plot.viewer import ViewerModel as _ViewerModel

from qtextraplot._napari.components.overlays.legend import (
    ColorLike as LegendColorLike,
)
from qtextraplot._napari.components.overlays.legend import (
    LegendEntry,
    LegendInput,
    LegendOverlay,
    legend_entries_from_points,
)

try:
    from pydantic.v1 import PrivateAttr
except ImportError:
    from pydantic import PrivateAttr

LEGEND_OVERLAY_NAME = "Legend"
POINTS_LAYER_ERROR = "Legend source layer must be a Points layer."
LEGEND_LAYER_EVENTS = (
    "data",
    "name",
    "visible",
    "color",
    "width",
    "face_color",
    "border_color",
    "symbol",
    "size",
)


def _layer_has_data(layer: Layer) -> bool:
    data = getattr(layer, "data", None)
    if data is None:
        return False
    with suppress(TypeError):
        return len(data) > 0
    return np.asarray(data).size > 0


def _first_value(value: ty.Any) -> ty.Any:
    if value is None:
        return None
    array = np.asarray(value, dtype=object)
    if array.ndim == 0:
        return array.item()
    if array.size == 0:
        return None
    return array.flat[0]


def _first_color(value: ty.Any) -> ty.Any:
    if value is None:
        return None
    array = np.asarray(value)
    if array.size == 0:
        return None
    if array.ndim <= 1:
        return array
    return array[0]


def _centroids_marker(layer: Centroids) -> str:
    orientation = getattr(layer.orientation, "value", layer.orientation)
    return "vbar" if str(orientation) == "vertical" else "hbar"


def legend_entry_from_layer(layer: Layer) -> LegendEntry | None:
    """Create one legend entry from a supported visible plot layer."""
    if not getattr(layer, "visible", False) or not _layer_has_data(layer):
        return None

    if isinstance(layer, Line):
        return LegendEntry(label=layer.name, marker="hbar", color=layer.color)
    if isinstance(layer, Centroids):
        return LegendEntry(label=layer.name, marker=_centroids_marker(layer), color=_first_color(layer.color))
    if isinstance(layer, (Scatter, Points)):
        color = _first_color(getattr(layer, "face_color", None))
        if color is None:
            color = _first_color(getattr(layer, "border_color", None))
        marker = _first_value(getattr(layer, "symbol", None))
        if marker is None:
            marker = getattr(layer, "current_symbol", None)
        return LegendEntry(label=layer.name, marker=marker, color=color)
    return None


def legend_entries_from_layers(layers: ty.Iterable[Layer]) -> tuple[LegendEntry, ...]:
    """Create legend entries from supported line-viewer layers."""
    entries = [entry for layer in layers if (entry := legend_entry_from_layer(layer)) is not None]
    return tuple(entries)


class Viewer(_ViewerModel):
    """Napari-plot viewer model with qtextraplot legend overlay APIs."""

    _legend_source_layers: list[Layer] = PrivateAttr(default_factory=list)

    def __init__(self, title: str = "napari_plot") -> None:
        super().__init__(title=title)
        self._overlays[LEGEND_OVERLAY_NAME] = LegendOverlay(visible=False, sync_with_source=True)
        self.layers.events.inserted.connect(self._on_legend_layers_change)
        self.layers.events.removed.connect(self._on_legend_layers_change)
        self.layers.events.reordered.connect(self._on_legend_layers_change)
        with suppress(AttributeError):
            self.layers.events.changed.connect(self._on_legend_layers_change)
        self._refresh_legend_source_connections()

    def legend_overlays(self) -> dict[str, LegendOverlay]:
        """Return legend overlays keyed by overlay name."""
        return {name: overlay for name, overlay in self._overlays.items() if isinstance(overlay, LegendOverlay)}

    @property
    def legend_visible(self) -> bool:
        """Whether any legend overlay is visible."""
        return any(overlay.visible for overlay in self.legend_overlays().values())

    def set_legend_visible(self, visible: bool) -> None:
        """Set visibility of all legend overlays."""
        for overlay in self.legend_overlays().values():
            overlay.visible = visible

    def set_legend(
        self,
        entries: LegendInput,
        *,
        name: str = LEGEND_OVERLAY_NAME,
        visible: bool = True,
        position: str = "top_right",
        text_color: LegendColorLike = "white",
        font_size: float = 10.0,
        marker_size: float = 10.0,
        row_spacing: float = 4.0,
        padding: float = 6.0,
        background_color: LegendColorLike = (0.0, 0.0, 0.0, 0.65),
        border_color: LegendColorLike = (1.0, 1.0, 1.0, 0.8),
        border_width: float = 1.0,
    ) -> LegendOverlay:
        """Set a named canvas legend overlay."""
        overlay = self._overlays.get(name)
        if not isinstance(overlay, LegendOverlay):
            overlay = LegendOverlay()
            self._overlays[name] = overlay

        overlay.source_layer = None
        overlay.sync_with_source = False
        overlay.visible = visible
        overlay.position = position
        overlay.text_color = text_color
        overlay.font_size = font_size
        overlay.marker_size = marker_size
        overlay.row_spacing = row_spacing
        overlay.padding = padding
        overlay.background_color = background_color
        overlay.border_color = border_color
        overlay.border_width = border_width
        overlay.set_entries(entries)
        self._refresh_legend_source_connections()
        return overlay

    def clear_legend(self, name: str = LEGEND_OVERLAY_NAME) -> None:
        """Clear a named canvas legend overlay."""
        overlay = self._overlays.get(name)
        if isinstance(overlay, LegendOverlay):
            del self._overlays[name]
        self._refresh_legend_source_connections()

    def set_legend_from_layers(
        self,
        *,
        name: str = LEGEND_OVERLAY_NAME,
        sync: bool = True,
        visible: bool = True,
        position: str = "top_right",
        text_color: LegendColorLike = "white",
        font_size: float = 10.0,
        marker_size: float = 10.0,
        row_spacing: float = 4.0,
        padding: float = 6.0,
        background_color: LegendColorLike = (0.0, 0.0, 0.0, 0.65),
        border_color: LegendColorLike = (1.0, 1.0, 1.0, 0.8),
        border_width: float = 1.0,
    ) -> LegendOverlay:
        """Create a named legend overlay from visible supported plot layers."""
        overlay = self.set_legend(
            legend_entries_from_layers(self.layers),
            name=name,
            visible=visible,
            position=position,
            text_color=text_color,
            font_size=font_size,
            marker_size=marker_size,
            row_spacing=row_spacing,
            padding=padding,
            background_color=background_color,
            border_color=border_color,
            border_width=border_width,
        )
        overlay.source_layer = None
        overlay.sync_with_source = sync
        self._refresh_legend_source_connections()
        return overlay

    def refresh_legend_from_layers(self, name: str = LEGEND_OVERLAY_NAME) -> LegendOverlay | None:
        """Refresh a layer-derived legend without changing its style."""
        overlay = self._overlays.get(name)
        if not isinstance(overlay, LegendOverlay):
            return None
        overlay.set_entries(legend_entries_from_layers(self.layers))
        return overlay

    def _resolve_points_layer(self, layer: str | Points) -> Points:
        """Resolve a Points layer name or object."""
        if isinstance(layer, str):
            return ty.cast(Points, self.layers[layer])
        if not isinstance(layer, Points):
            raise TypeError(POINTS_LAYER_ERROR)
        return layer

    def _legend_source_layer(self, overlay: LegendOverlay) -> Points | None:
        """Return the source Points layer for a point-derived legend overlay."""
        if overlay.source_layer is None:
            return None
        with suppress(KeyError):
            layer = self.layers[overlay.source_layer]
            if isinstance(layer, Points):
                return layer
        return None

    def refresh_legend_from_source(self, name: str = LEGEND_OVERLAY_NAME) -> LegendOverlay | None:
        """Refresh a point-derived legend without changing its style."""
        overlay = self._overlays.get(name)
        if not isinstance(overlay, LegendOverlay):
            return None
        layer = self._legend_source_layer(overlay)
        if layer is None:
            return overlay
        with suppress(ValueError, KeyError):
            overlay.set_entries(
                legend_entries_from_points(
                    layer,
                    label_property=overlay.label_property,
                    color_source=overlay.color_source,
                    marker_source=overlay.marker_source,
                    group_by_style=overlay.group_by_style,
                ),
            )
        return overlay

    def set_legend_auto_sync(self, name: str = LEGEND_OVERLAY_NAME, enabled: bool = True) -> LegendOverlay | None:
        """Enable or disable live refresh for a legend overlay."""
        overlay = self._overlays.get(name)
        if not isinstance(overlay, LegendOverlay):
            return None
        overlay.sync_with_source = enabled
        if enabled:
            if overlay.source_layer is None:
                self.refresh_legend_from_layers(name)
            else:
                self.refresh_legend_from_source(name)
        self._refresh_legend_source_connections()
        return overlay

    def set_legend_from_points(
        self,
        layer: str | Points,
        *,
        label_property: str = "label",
        name: str = LEGEND_OVERLAY_NAME,
        color_source: str = "face",
        marker_source: str = "symbol",
        group_by_style: bool = True,
        sync: bool = False,
        visible: bool = True,
        position: str = "top_right",
        text_color: LegendColorLike = "white",
        font_size: float = 10.0,
        marker_size: float = 10.0,
        row_spacing: float = 4.0,
        padding: float = 6.0,
        background_color: LegendColorLike = (0.0, 0.0, 0.0, 0.65),
        border_color: LegendColorLike = (1.0, 1.0, 1.0, 0.8),
        border_width: float = 1.0,
    ) -> LegendOverlay:
        """Create a named legend overlay from a Points layer."""
        points_layer = self._resolve_points_layer(layer)
        overlay = self.set_legend(
            legend_entries_from_points(
                points_layer,
                label_property=label_property,
                color_source=color_source,
                marker_source=marker_source,
                group_by_style=group_by_style,
            ),
            name=name,
            visible=visible,
            position=position,
            text_color=text_color,
            font_size=font_size,
            marker_size=marker_size,
            row_spacing=row_spacing,
            padding=padding,
            background_color=background_color,
            border_color=border_color,
            border_width=border_width,
        )
        overlay.source_layer = points_layer.name
        overlay.label_property = label_property
        overlay.color_source = color_source
        overlay.marker_source = marker_source
        overlay.group_by_style = group_by_style
        overlay.sync_with_source = sync
        self._refresh_legend_source_connections()
        return overlay

    def _on_legend_layers_change(self, _event=None) -> None:
        """Refresh automatic legend state after layer collection changes."""
        self._refresh_legend_source_connections()
        self._on_legend_source_change()

    def _disconnect_legend_source_layer(self, layer: Layer) -> None:
        for event_name in LEGEND_LAYER_EVENTS:
            with suppress(AttributeError, KeyError, ValueError):
                getattr(layer.events, event_name).disconnect(self._on_legend_source_change)

    def _connect_legend_source_layer(self, layer: Layer) -> None:
        for event_name in LEGEND_LAYER_EVENTS:
            with suppress(AttributeError, KeyError):
                getattr(layer.events, event_name).connect(self._on_legend_source_change)

    def _refresh_legend_source_connections(self, _event=None) -> None:
        """Reconnect live legend source listeners."""
        for layer in self._legend_source_layers:
            self._disconnect_legend_source_layer(layer)

        self._legend_source_layers = []
        for overlay in self.legend_overlays().values():
            if not overlay.sync_with_source:
                continue
            if overlay.source_layer is not None:
                layer = self._legend_source_layer(overlay)
                if layer is not None and not any(layer is current for current in self._legend_source_layers):
                    self._legend_source_layers.append(layer)
                continue
            for layer in self.layers:
                if isinstance(layer, (Line, Centroids, Scatter, Points)) and not any(
                    layer is current for current in self._legend_source_layers
                ):
                    self._legend_source_layers.append(layer)

        for layer in self._legend_source_layers:
            self._connect_legend_source_layer(layer)

    def _on_legend_source_change(self, _event=None) -> None:
        """Refresh synced legends from their configured sources."""
        for name, overlay in self.legend_overlays().items():
            if not overlay.sync_with_source:
                continue
            if overlay.source_layer is None:
                self.refresh_legend_from_layers(name)
            else:
                self.refresh_legend_from_source(name)


__all__ = [
    "LEGEND_OVERLAY_NAME",
    "Viewer",
    "legend_entries_from_layers",
    "legend_entry_from_layer",
]
