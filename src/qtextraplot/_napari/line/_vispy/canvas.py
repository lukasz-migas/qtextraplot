"""Modified canvas."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from napari.components._viewer_constants import CanvasPosition
from napari.components.overlays import CanvasOverlay, Overlay
from napari.utils.events import disconnect_events
from napari_plot._vispy.canvas import VispyCanvas as _VispyCanvas

CANVAS_OVERLAY_PADDING = 10.0


class VispyCanvas(_VispyCanvas):
    """Line canvas with qtextraplot overlay lifecycle support."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        super().__init__(*args, **kwargs)
        self.viewer._overlays.events.added.connect(self._on_overlay_added)
        self.viewer._overlays.events.removed.connect(self._on_overlay_removed)
        self.viewer._overlays.events.changed.connect(self._on_overlay_changed)

    def _on_mouse_double_click(self, event) -> None:
        """Process mouse double-click events, including modified clicks."""
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
        self._disconnect_canvas_overlay_events(overlay)
        vispy_overlay = self._overlay_to_visual.pop(overlay, None)
        if vispy_overlay is None:
            return
        with suppress(Exception):
            vispy_overlay.close()
        with suppress(AttributeError):
            vispy_overlay.node.parent = None
        self._request_canvas_update()

    def _add_overlay_to_visual(self, overlay: Overlay) -> None:
        """Create an overlay visual and configure canvas positioning."""
        super()._add_overlay_to_visual(overlay)
        if isinstance(overlay, CanvasOverlay):
            self._connect_canvas_overlay_events(overlay)
            self._overlay_to_visual[overlay].canvas_position_callback = self._update_overlay_canvas_positions
            self._update_overlay_canvas_positions()

    def _connect_canvas_overlay_events(self, overlay: CanvasOverlay) -> None:
        """Connect events that can affect canvas overlay placement."""
        overlay.events.position.connect(self._request_canvas_update)
        overlay.events.visible.connect(self._request_canvas_update)

    def _disconnect_canvas_overlay_events(self, overlay: Overlay) -> None:
        """Disconnect canvas positioning events for an overlay."""
        if not isinstance(overlay, CanvasOverlay):
            return
        with suppress(AttributeError, KeyError, ValueError):
            overlay.events.position.disconnect(self._request_canvas_update)
        with suppress(AttributeError, KeyError, ValueError):
            overlay.events.visible.disconnect(self._request_canvas_update)

    def _update_overlay_canvas_positions(self, _event=None) -> None:
        """Position visible canvas overlays within the plot view."""
        x_padding = y_padding = CANVAS_OVERLAY_PADDING
        x_offsets = dict.fromkeys(CanvasPosition, x_padding)
        y_offsets = dict.fromkeys(CanvasPosition, y_padding)
        x_max, y_max = self.view.size

        for overlay, vispy_overlay in self._overlay_to_visual.items():
            if (
                not overlay.visible
                or not isinstance(overlay, CanvasOverlay)
                or not isinstance(overlay.position, CanvasPosition)
            ):
                continue

            position = overlay.position
            x_offset = x_offsets[position]
            y_offset = y_offsets[position]

            if position in (CanvasPosition.TOP_RIGHT, CanvasPosition.BOTTOM_LEFT):
                x_offsets[position] += vispy_overlay.x_size + x_padding
            else:
                y_offsets[position] += vispy_overlay.y_size + y_padding

            y = (
                y_offset
                if position
                in (
                    CanvasPosition.TOP_LEFT,
                    CanvasPosition.TOP_CENTER,
                    CanvasPosition.TOP_RIGHT,
                )
                else y_max - vispy_overlay.y_size - y_offset
            )

            if position in (CanvasPosition.TOP_LEFT, CanvasPosition.BOTTOM_LEFT):
                x = x_offset
            elif position in (CanvasPosition.TOP_RIGHT, CanvasPosition.BOTTOM_RIGHT):
                x = x_max - vispy_overlay.x_size - x_offset
            else:
                x = (x_max - vispy_overlay.x_size) / 2

            vispy_overlay.node.transform.translate = [x, y, 0, 0]

    def _request_canvas_update(self, _event=None) -> None:
        """Request a canvas redraw after overlay collection changes."""
        self._update_overlay_canvas_positions()
        with suppress(AttributeError):
            self._scene_canvas.update()

    def on_resize(self, event) -> None:
        """Update overlay placement after the plot canvas is resized."""
        super().on_resize(event)
        self._request_canvas_update()

    def close(self) -> None:
        """Disconnect overlay collection listeners."""
        for overlay in tuple(self._overlay_to_visual):
            self._disconnect_canvas_overlay_events(overlay)
        disconnect_events(self.viewer._overlays.events, self)
        super().close()
