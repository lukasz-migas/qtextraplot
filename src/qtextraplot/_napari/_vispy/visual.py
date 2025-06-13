"""Create overlays."""

from napari._vispy.overlays.interaction_box import VispySelectionBoxOverlay
from napari._vispy.utils.visual import create_vispy_overlay, overlay_to_visual

from qtextraplot._napari._vispy.overlays.color_bar_mpl import VispyColorbarOverlay
from qtextraplot._napari._vispy import VispyCrosshairOverlay
from qtextraplot._napari.components.overlays.color_bar import ColorBarOverlay
from qtextraplot._napari.components.overlays.crosshair import CrossHairOverlay
from qtextraplot._napari.image.components.zoom import ZoomOverlay

overlay_to_visual.update(
    {
        CrossHairOverlay: VispyCrosshairOverlay,
        ColorBarOverlay: VispyColorbarOverlay,
        ZoomOverlay: VispySelectionBoxOverlay,
    }
)

__all__ = ["create_vispy_overlay", "overlay_to_visual"]
