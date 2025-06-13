"""Vispy."""

from napari._vispy.utils.visual import overlay_to_visual

from qtextraplot._napari._vispy.overlays.color_bar_mpl import VispyColorbarOverlay
from qtextraplot._napari._vispy import VispyCrosshairOverlay
from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.image._vispy.zoom import VispyZoomOverlay
from qtextraplot._napari.image.components.zoom import ZoomOverlay


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update(
        {
            ColorBarOverlay: VispyColorbarOverlay,
            CrossHairOverlay: VispyCrosshairOverlay,
            ZoomOverlay: VispyZoomOverlay,
        }
    )
