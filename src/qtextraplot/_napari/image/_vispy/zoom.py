from contextlib import suppress

from napari._vispy.overlays.base import ViewerOverlayMixin, VispySceneOverlay
from napari._vispy.visuals.interaction_box import InteractionBox as _InteractionBox


class InteractionBox(_InteractionBox):
    def _compute_bounds(self, axis, view):
        bounds = None
        with suppress(ValueError):
            for v in view._subvisuals:
                if v.visible:
                    vb = v.bounds(axis)
                    if bounds is None:
                        bounds = vb
                    elif vb is not None:
                        bounds = [min(bounds[0], vb[0]), max(bounds[1], vb[1])]
        return bounds


class VispyZoomOverlay(ViewerOverlayMixin, VispySceneOverlay):
    """Zoom box overlay.."""

    def __init__(self, viewer, overlay, parent=None):
        super().__init__(
            node=InteractionBox(),
            viewer=viewer,
            overlay=overlay,
            parent=parent,
        )

        self.overlay.events.bounds.connect(self._on_bounds_change)

        self.node._marker_color = (1, 0, 1, 1)
        self.node._highlight_width = 4

        self._on_visible_change()
        self._on_bounds_change(None)

    def _on_bounds_change(self, _evt=None):
        """Change position."""
        if self.viewer.dims.ndim == 2:
            top_left, bot_right = self.overlay.bounds
            self.node.set_data(
                # invert axes for vispy
                top_left[::-1],
                bot_right[::-1],
                handles=None,
                selected=None,
            )

    def reset(self):
        super().reset()
        self._on_bounds_change()
