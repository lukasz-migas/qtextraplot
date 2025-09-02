from napari._vispy.utils.visual import overlay_to_visual


def register_vispy_overlays():
    """Register vispy overlays."""
    overlay_to_visual.update({})
