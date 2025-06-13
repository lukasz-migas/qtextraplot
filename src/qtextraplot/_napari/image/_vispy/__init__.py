from napari._vispy.utils.visual import overlay_to_visual

from qtextraplot._napari.image._vispy.zoom import VispyZoomOverlay
from qtextraplot._napari.image.components.zoom import ZoomOverlay


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update(
        {
            ZoomOverlay: VispyZoomOverlay,
        }
    )
