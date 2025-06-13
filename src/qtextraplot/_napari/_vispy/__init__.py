from napari._vispy.utils.visual import create_vispy_overlay, overlay_to_visual

from qtextraplot._napari._vispy.overlays.color_bar_mpl import ColorBarOverlay, VispyColorbarOverlay
from qtextraplot._napari._vispy.overlays.crosshair import CrossHairOverlay, VispyCrosshairOverlay


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update(
        {
            ColorBarOverlay: VispyColorbarOverlay,
            CrossHairOverlay: VispyCrosshairOverlay,
        }
    )


__all__ = [
    "VispyColorbarOverlay",
    "VispyCrosshairOverlay",
    "create_vispy_overlay",
    "overlay_to_visual",
    "register_vispy_overlays",
]
