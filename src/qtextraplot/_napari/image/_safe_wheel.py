"""Safe mouse-wheel routing for napari image canvases."""

from __future__ import annotations

import typing as ty

from vispy.scene.events import SceneMouseEvent

if ty.TYPE_CHECKING:
    from collections.abc import Callable


def install_safe_wheel_handler(canvas: ty.Any) -> None:
    """Route mouse-wheel events without VisPy's GL picking render."""
    scene_canvas = canvas._scene_canvas
    scene_canvas.events.mouse_wheel.disconnect(scene_canvas._process_mouse_event)
    scene_canvas.events.mouse_wheel.connect(_make_safe_wheel_handler(canvas))


def _make_safe_wheel_handler(canvas: ty.Any) -> Callable[[ty.Any], None]:
    """Create a no-picking mouse-wheel handler for a napari VispyCanvas."""

    def _safe_wheel_handler(event: ty.Any) -> None:
        if event.type == "mouse_wheel" and len(event.modifiers) > 0:
            return
        if event.handled or event.pos is None:
            return

        viewbox, _grid_coords = canvas._get_viewbox_at(event.pos)
        if viewbox is None:
            event.handled = True
            return

        scene_event = SceneMouseEvent(event=event, visual=viewbox)
        viewbox.events.mouse_wheel(scene_event)
        event.handled = scene_event.handled

    return _safe_wheel_handler
