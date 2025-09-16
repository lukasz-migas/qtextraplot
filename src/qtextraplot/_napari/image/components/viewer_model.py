"""Viewer model."""

from __future__ import annotations

import typing as ty
from weakref import WeakSet

from napari.components.viewer_model import ViewerModel as _ViewerModel
from napari.utils.events.event import Event

from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.image.components._viewer_mouse_bindings import crosshair, double_click_to_zoom_reset

if ty.TYPE_CHECKING:
    from napari.layers import Image, Labels

DEFAULT_OVERLAYS = {
    "cross_hair": CrossHairOverlay,
    "color_bar": ColorBarOverlay,
}


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

        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})

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

    def clear_canvas(self) -> None:
        """Remove all layers from the canvas."""
        self.layers.select_all()
        self.layers.remove_selected()
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
