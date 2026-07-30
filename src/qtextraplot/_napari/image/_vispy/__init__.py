from napari._vispy.utils.visual import overlay_to_visual
from napari.components.overlays import ColorBarOverlay

from qtextraplot._napari.image._vispy.color_bar import _SafeVispyColorBarOverlay


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update({ColorBarOverlay: _SafeVispyColorBarOverlay})
