"""Keyboard shortcuts."""

from qtextraplot._napari.line.components.viewer_model import Viewer


@Viewer.bind_key("Control-Backspace")
@Viewer.bind_key("Control-Delete")
def remove_selected(viewer: Viewer) -> None:
    """Remove selected layers."""
    viewer.layers.remove_selected()


@Viewer.bind_key("Control-A")
def select_all(viewer: Viewer) -> None:
    """Selected all layers."""
    viewer.layers.select_all()


@Viewer.bind_key("Control-Shift-Backspace")
@Viewer.bind_key("Control-Shift-Delete")
def remove_all_layers(viewer: Viewer) -> None:
    """Remove all layers."""
    viewer.layers.select_all()
    viewer.layers.remove_selected()


@Viewer.bind_key("Up")
def select_layer_above(viewer: Viewer) -> None:
    """Select layer above."""
    viewer.layers.select_next()


@Viewer.bind_key("Down")
def select_layer_below(viewer: Viewer) -> None:
    """Select layer below."""
    viewer.layers.select_previous()


@Viewer.bind_key("Shift-Up")
def also_select_layer_above(viewer: Viewer) -> None:
    """Also select layer above."""
    viewer.layers.select_next(shift=True)


@Viewer.bind_key("Shift-Down")
def also_select_layer_below(viewer: Viewer) -> None:
    """Also select layer below."""
    viewer.layers.select_previous(shift=True)


@Viewer.bind_key("Control-R")
def reset_view(viewer: Viewer) -> None:
    """Reset view to original state."""
    viewer.reset_view()


@Viewer.bind_key("Control-G")
def toggle_grid(viewer: Viewer) -> None:
    """Toggle grid mode."""
    viewer.grid.enabled = not viewer.grid.enabled


@Viewer.bind_key("V")
def toggle_selected_visibility(viewer: Viewer) -> None:
    """Toggle visibility of selected layers."""
    viewer.layers.toggle_selected_visibility()


@Viewer.bind_key("Control-L")
def toggle_selected_editability(viewer: Viewer) -> None:
    """Toggle visibility of selected layers."""
    viewer.layers.toggle_selected_editable()
