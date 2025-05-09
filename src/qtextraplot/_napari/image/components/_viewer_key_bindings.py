"""Keyboard shortcuts."""

from qtextraplot._napari.image.components.viewer_model import Viewer


@Viewer.bind_key("Control")
def reset_scroll_progress(viewer):
    """Reset dims scroll progress."""
    # on key press
    viewer.dims._scroll_progress = 0
    yield
    # on key release
    viewer.dims._scroll_progress = 0


@Viewer.bind_key("Control-Y")
def toggle_ndisplay(viewer):
    """Toggle ndisplay."""
    if viewer.dims.ndisplay == 3:
        viewer.dims.ndisplay = 2
    else:
        viewer.dims.ndisplay = 3


@Viewer.bind_key("Left")
def increment_dims_left(viewer):
    """Increment dimensions slider to the left."""
    viewer.dims._increment_dims_left()


@Viewer.bind_key("Right")
def increment_dims_right(viewer):
    """Increment dimensions slider to the right."""
    viewer.dims._increment_dims_right()


@Viewer.bind_key("Alt-Up")
def focus_axes_up(viewer):
    """Move focus of dimensions slider up."""
    viewer.dims._focus_up()


@Viewer.bind_key("Alt-Down")
def focus_axes_down(viewer):
    """Move focus of dimensions slider down."""
    viewer.dims._focus_down()


@Viewer.bind_key("Control-E")
def roll_axes(viewer):
    """Change order of the visible axes, e.g. [0, 1, 2] -> [2, 0, 1]."""
    viewer.dims._roll()


@Viewer.bind_key("Control-T")
def transpose_axes(viewer):
    """Transpose order of the last two visible axes, e.g. [0, 1] -> [1, 0]."""
    viewer.dims._transpose()


@Viewer.bind_key("Control-Backspace")
@Viewer.bind_key("Control-Delete")
def remove_selected(viewer):
    """Remove selected layers."""
    viewer.layers.remove_selected()


@Viewer.bind_key("Control-A")
def select_all(viewer):
    """Selected all layers."""
    viewer.layers.select_all()


@Viewer.bind_key("Control-Shift-Backspace")
@Viewer.bind_key("Control-Shift-Delete")
def remove_all_layers(viewer):
    """Remove all layers."""
    viewer.layers.select_all()
    viewer.layers.remove_selected()


@Viewer.bind_key("Up")
def select_layer_above(viewer):
    """Select layer above."""
    viewer.layers.select_next()


@Viewer.bind_key("Down")
def select_layer_below(viewer):
    """Select layer below."""
    viewer.layers.select_previous()


@Viewer.bind_key("Shift-Up")
def also_select_layer_above(viewer):
    """Also select layer above."""
    viewer.layers.select_next(shift=True)


@Viewer.bind_key("Shift-Down")
def also_select_layer_below(viewer):
    """Also select layer below."""
    viewer.layers.select_previous(shift=True)


@Viewer.bind_key("Control-R")
def reset_view(viewer):
    """Reset view to original state."""
    viewer.reset_view()


@Viewer.bind_key("Control-G")
def toggle_grid(viewer):
    """Toggle grid mode."""
    viewer.grid.enabled = not viewer.grid.enabled


@Viewer.bind_key("V")
def toggle_selected_visibility(viewer):
    """Toggle visibility of selected layers."""
    viewer.layers.toggle_selected_visibility()


@Viewer.bind_key("Control-L")
def toggle_selected_editability(viewer):
    """Toggle visibility of selected layers."""
    viewer.layers.toggle_selected_editable()
