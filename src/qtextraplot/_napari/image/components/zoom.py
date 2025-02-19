"""Zoom-box."""

import typing as ty

from napari.components.overlays.base import SceneOverlay
from napari.layers.utils.interaction_box import InteractionBoxHandle


class ZoomOverlay(SceneOverlay):
    """A box that can be used to select and transform objects.

    Attributes
    ----------
    bounds : 2-tuple of 2-tuples
        Corners at top left and bottom right in layer coordinates.
    handles : bool
        Whether to show the handles for transfomation or just the box.
    selected_handle : Optional[InteractionBoxHandle]
        The currently selected handle.
    visible : bool
        If the overlay is visible or not.
    opacity : float
        The opacity of the overlay. 0 is fully transparent.
    order : int
        The rendering order of the overlay: lower numbers get rendered first.
    """

    bounds: tuple[tuple[float, float], tuple[float, float]] = ((0, 0), (0, 0))
    handles: bool = False
    selected_handle: ty.Optional[InteractionBoxHandle] = None

    def extents(self) -> tuple[float, float, float, float]:
        """Return the extents of the overlay in the scene coordinates.

        Returns
        -------
        extents : tuple of 4 floats
            The extents of the overlay in the scene coordinates.
            x_min, x_max, y_min, y_max
        """
        top_left, bot_right = self.bounds
        y_min = min(top_left[0], bot_right[0])
        y_max = max(top_left[0], bot_right[0])
        x_min = min(top_left[1], bot_right[1])
        x_max = max(top_left[1], bot_right[1])
        return x_min, x_max, y_min, y_max
