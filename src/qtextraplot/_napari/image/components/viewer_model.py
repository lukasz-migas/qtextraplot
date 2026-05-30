"""Viewer model."""

from __future__ import annotations

import typing as ty
from contextlib import suppress
from weakref import WeakSet

from napari.components.viewer_model import ViewerModel as _ViewerModel
from napari.layers import Image, Layer, Points
from napari.utils.events.event import Event

from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.components.overlays.legend import (
    ColorLike as LegendColorLike,
)
from qtextraplot._napari.components.overlays.legend import (
    LegendInput,
    LegendOverlay,
    legend_entries_from_points,
)
from qtextraplot._napari.components.overlays.object_outlines import (
    ColorLike,
    ObjectOutlinesOverlay,
    OutlineInput,
    WidthLike,
)
from qtextraplot._napari.image.components._viewer_mouse_bindings import crosshair, double_click_to_zoom_reset

try:
    from pydantic.v1 import PrivateAttr
except ImportError:
    from pydantic import PrivateAttr

if ty.TYPE_CHECKING:
    from napari.layers import Labels

DEFAULT_OVERLAYS = {
    "cross_hair": CrossHairOverlay,
    "color_bar": ColorBarOverlay,
}
LEGEND_OVERLAY_NAME = "Legend"
POINTS_LAYER_ERROR = "Legend source layer must be a Points layer."
LEGEND_SOURCE_EVENTS = ("data", "face_color", "border_color", "symbol", "properties", "features")
OBJECT_OUTLINES_OVERLAY_NAME = "Object outlines"


class Viewer(_ViewerModel):
    """Viewer model."""

    _instances: ty.ClassVar[WeakSet[Viewer]] = WeakSet()
    _legend_source_layers: list[Points] = PrivateAttr(default_factory=list)

    def __init__(self, title: str = "qtextraplot", **kwargs: ty.Any):
        super().__init__(title=title)

        if kwargs.get("allow_crosshair", True):
            self.mouse_drag_callbacks.append(crosshair)
        if kwargs.get("allow_double_click_reset", True):
            self.mouse_double_click_callbacks.clear()
            self.mouse_double_click_callbacks.append(double_click_to_zoom_reset)

        for key, value in DEFAULT_OVERLAYS.items():
            self._overlays[key] = value()
        # self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})
        self.events.add(crosshair=Event, zoom=Event, clear_canvas=Event)
        self.layers.events.inserted.connect(self._refresh_legend_source_connections)
        self.layers.events.removed.connect(self._refresh_legend_source_connections)
        self.layers.events.changed.connect(self._refresh_legend_source_connections)
        self._instances.add(self)

    @property
    def cross_hair(self) -> CrossHairOverlay:
        """Crosshair overlay."""
        return self._overlays["cross_hair"]

    @property
    def color_bar(self) -> ColorBarOverlay:
        """Colorbar overlay."""
        return self._overlays["color_bar"]

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
        """Clear a named legend overlay."""
        overlay = self._overlays.get(name)
        if isinstance(overlay, LegendOverlay):
            del self._overlays[name]
        self._refresh_legend_source_connections()

    def _resolve_points_layer(self, layer: str | Points) -> Points:
        """Resolve a Points layer name or object."""
        if isinstance(layer, str):
            return ty.cast(Points, self.layers[layer])
        if not isinstance(layer, Points):
            raise TypeError(POINTS_LAYER_ERROR)
        return layer

    def _legend_source_layer(self, overlay: LegendOverlay) -> Points | None:
        """Return the source Points layer for a legend overlay."""
        if overlay.source_layer is None:
            return None
        with suppress(KeyError):
            layer = self.layers[overlay.source_layer]
            if isinstance(layer, Points):
                return layer
        return None

    def _disconnect_legend_source_layer(self, layer: Points) -> None:
        for event_name in LEGEND_SOURCE_EVENTS:
            with suppress(AttributeError, KeyError, ValueError):
                getattr(layer.events, event_name).disconnect(self._on_legend_source_change)

    def _connect_legend_source_layer(self, layer: Points) -> None:
        for event_name in LEGEND_SOURCE_EVENTS:
            with suppress(AttributeError, KeyError):
                getattr(layer.events, event_name).connect(self._on_legend_source_change)

    def _refresh_legend_source_connections(self, _event=None) -> None:
        """Reconnect optional live legend source listeners."""
        for layer in self._legend_source_layers:
            self._disconnect_legend_source_layer(layer)

        self._legend_source_layers = []
        for overlay in self.legend_overlays().values():
            if not overlay.sync_with_source:
                continue
            layer = self._legend_source_layer(overlay)
            if layer is not None and not any(layer is current for current in self._legend_source_layers):
                self._legend_source_layers.append(layer)
        for layer in self._legend_source_layers:
            self._connect_legend_source_layer(layer)

    def _on_legend_source_change(self, _event=None) -> None:
        """Refresh all synced point-derived legends."""
        for name, overlay in self.legend_overlays().items():
            if overlay.sync_with_source:
                self.refresh_legend_from_source(name)

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
        """Enable or disable live refresh for a point-derived legend."""
        overlay = self._overlays.get(name)
        if not isinstance(overlay, LegendOverlay):
            return None
        overlay.sync_with_source = enabled
        if enabled:
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
        entries = legend_entries_from_points(
            points_layer,
            label_property=label_property,
            color_source=color_source,
            marker_source=marker_source,
            group_by_style=group_by_style,
        )
        overlay = self.set_legend(
            entries,
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

    def object_outline_overlays(self) -> dict[str, ObjectOutlinesOverlay]:
        """Return object outline overlays keyed by overlay name."""
        return {name: overlay for name, overlay in self._overlays.items() if isinstance(overlay, ObjectOutlinesOverlay)}

    @property
    def object_outlines_visible(self) -> bool:
        """Whether any object outline overlay is visible."""
        return any(overlay.visible for overlay in self.object_outline_overlays().values())

    def set_object_outlines_visible(self, visible: bool) -> None:
        """Set visibility of all object outline overlays."""
        for overlay in self.object_outline_overlays().values():
            overlay.visible = visible

    def _resolve_object_outline_target_layer(self, target_layer: str | Layer | None) -> str | None:
        """Resolve an outline target layer to its current layer name."""
        if isinstance(target_layer, str):
            return target_layer
        if target_layer is not None:
            return target_layer.name

        active_layer = self.layers.selection.active
        if isinstance(active_layer, Image):
            return active_layer.name
        for layer in reversed(self.layers):
            if isinstance(layer, Image):
                return layer.name
        return None

    def set_object_outlines(
        self,
        outlines: OutlineInput,
        *,
        name: str = OBJECT_OUTLINES_OVERLAY_NAME,
        target_layer: str | Layer | None = None,
        color: ColorLike = "red",
        width: WidthLike = 1.0,
        closed: bool = True,
        visible: bool = True,
    ) -> ObjectOutlinesOverlay:
        """Set a named object outline overlay."""
        resolved_target_layer = self._resolve_object_outline_target_layer(target_layer)
        overlay = self._overlays.get(name)
        if not isinstance(overlay, ObjectOutlinesOverlay):
            overlay = ObjectOutlinesOverlay(target_layer=resolved_target_layer, closed=closed, visible=visible)
            self._overlays[name] = overlay

        overlay.target_layer = resolved_target_layer
        overlay.closed = closed
        overlay.visible = visible
        overlay.set_outlines(outlines, color=color, width=width)
        return overlay

    def clear_object_outlines(self, name: str | None = None) -> None:
        """Clear one or all object outline overlays."""
        if name is not None:
            overlay = self._overlays.get(name)
            if isinstance(overlay, ObjectOutlinesOverlay):
                del self._overlays[name]
            return

        for overlay_name, overlay in list(self._overlays.items()):
            if isinstance(overlay, ObjectOutlinesOverlay):
                del self._overlays[overlay_name]

    def clear_canvas(self) -> None:
        """Remove all layers from the canvas."""
        self.layers.select_all()
        self.layers.remove_selected()
        self.clear_object_outlines()
        self.events.clear_canvas()

    def new_labels_for_image(self, image: Image, name: str) -> Labels:
        """Create a new labels layer for a given image layer."""
        import numpy as np

        layers_extent = self.layers.extent
        extent = layers_extent.world
        scale = layers_extent.step
        corner = extent[0]
        empty_labels = np.zeros(image.data.shape, dtype=np.uint8)
        return self.add_labels(empty_labels, translate=np.array(corner), scale=scale, name=name)
