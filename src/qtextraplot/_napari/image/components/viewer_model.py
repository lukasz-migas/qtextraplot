"""Viewer model."""

from __future__ import annotations

import typing as ty

from napari.components.viewer_model import ViewerModel as _ViewerModel
from napari.utils.events.event import Event

from qtextraplot._napari.common.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.common.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.image.components._viewer_mouse_bindings import crosshair

DEFAULT_OVERLAYS = {
    "cross_hair": CrossHairOverlay,
    "color_bar": ColorBarOverlay,
}


class ViewerModel(_ViewerModel):
    """Viewer model."""

    def __init__(self, title: str = "qtextraplot", **kwargs: ty.Any):
        super().__init__(title=title)

        if kwargs.get("allow_crosshair", True):
            self.mouse_drag_callbacks.append(crosshair)

        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})

        self.events.add(crosshair=Event, clear_canvas=Event)

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
