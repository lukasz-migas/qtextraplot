"""Modified canvas."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from napari.components.overlays import Overlay
from napari.utils.events import disconnect_events
from napari_plot._vispy.canvas import VispyCanvas as _VispyCanvas


class VispyCanvas(_VispyCanvas):
    """Line canvas with qtextraplot overlay lifecycle support."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        super().__init__(*args, **kwargs)
        self.viewer._overlays.events.added.connect(self._on_overlay_added)
        self.viewer._overlays.events.removed.connect(self._on_overlay_removed)
        self.viewer._overlays.events.changed.connect(self._on_overlay_changed)

    def _on_mouse_double_click(self, event) -> None:
        """Process mouse double click event."""
        if event.modifiers:
            return
        super()._on_mouse_double_click(event)

    def _on_overlay_added(self, event) -> None:
        """Create the visual for a newly added overlay."""
        overlay = event.value
        if overlay not in self._overlay_to_visual:
            self._add_overlay_to_visual(overlay)
            self._request_canvas_update()

    def _on_overlay_removed(self, event) -> None:
        """Remove the visual for a removed overlay."""
        self._remove_overlay_visual(event.value)

    def _on_overlay_changed(self, event) -> None:
        """Replace the visual when an overlay mapping is replaced."""
        old_overlay = getattr(event, "old_value", None)
        if old_overlay is not None:
            self._remove_overlay_visual(old_overlay)
        self._on_overlay_added(event)

    def _remove_overlay_visual(self, overlay: Overlay) -> None:
        """Close and detach a removed overlay visual."""
        vispy_overlay = self._overlay_to_visual.pop(overlay, None)
        if vispy_overlay is None:
            return
        with suppress(Exception):
            vispy_overlay.close()
        with suppress(AttributeError):
            vispy_overlay.node.parent = None
        self._request_canvas_update()

    def _request_canvas_update(self) -> None:
        """Request a canvas redraw after overlay collection changes."""
        with suppress(AttributeError):
            self._scene_canvas.update()

    def close(self) -> None:
        """Disconnect overlay collection listeners."""
        disconnect_events(self.viewer._overlays.events, self)
        super().close()
