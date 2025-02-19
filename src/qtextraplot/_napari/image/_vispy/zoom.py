from napari._vispy.overlays.base import ViewerOverlayMixin, VispySceneOverlay
from napari._vispy.visuals.interaction_box import InteractionBox


class VispyZoomOverlay(ViewerOverlayMixin, VispySceneOverlay):
    """Cross-hair."""

    def __init__(self, viewer, overlay, parent=None):
        super().__init__(
            node=InteractionBox(),
            viewer=viewer,
            overlay=overlay,
            parent=parent,
        )

        self.overlay.events.bounds.connect(self._on_bounds_change)
        self.overlay.events.handles.connect(self._on_bounds_change)
        self.overlay.events.selected_handle.connect(self._on_bounds_change)

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
                handles=self.overlay.handles,
                selected=self.overlay.selected_handle,
            )

    def reset(self):
        super().reset()
        self._on_bounds_change()
