"""Viewer model."""

from __future__ import annotations

import typing as ty
from weakref import WeakSet

from napari.components.viewer_model import ViewerModel as _ViewerModel
from napari.layers import Image
from napari.utils.events.event import Event

from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.components.overlays.object_outlines import (
    ColorLike,
    ObjectOutlinesOverlay,
    OutlineInput,
    WidthLike,
)
from qtextraplot._napari.image.components._viewer_mouse_bindings import crosshair, double_click_to_zoom_reset

if ty.TYPE_CHECKING:
    from napari.layers import Labels, Layer

DEFAULT_OVERLAYS = {
    "cross_hair": CrossHairOverlay,
    "color_bar": ColorBarOverlay,
}
OBJECT_OUTLINES_OVERLAY_NAME = "Object outlines"


class Viewer(_ViewerModel):
    """Viewer model."""

    _instances: ty.ClassVar[WeakSet[Viewer]] = WeakSet()

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
        self._instances.add(self)

    @property
    def cross_hair(self) -> CrossHairOverlay:
        """Crosshair overlay."""
        return self._overlays["cross_hair"]

    @property
    def color_bar(self) -> ColorBarOverlay:
        """Colorbar overlay."""
        return self._overlays["color_bar"]

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
