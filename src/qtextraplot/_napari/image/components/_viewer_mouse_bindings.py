"""Mouse bindings to the viewer."""


def crosshair(viewer, event):
    """Enable crosshair."""
    if "Control" not in event.modifiers:
        return

    if not viewer.cross_hair.visible:
        viewer.cross_hair.visible = True

    # on mouse press
    if event.type == "mouse_press":
        viewer.cross_hair.position = event.position
        viewer.events.crosshair(position=event.position)
        yield

    # on mouse move
    while event.type == "mouse_move" and "Control" in event.modifiers:
        viewer.cross_hair.position = event.position
        viewer.events.crosshair(position=event.position)
        yield

    # on mouse release
    if viewer.cross_hair.auto_hide:
        viewer.cross_hair.visible = False
    yield


def zoom(viewer, event):
    """Enable zoom."""
    if "Shift" not in event.modifiers:
        return

    if not viewer.zoom_box.visible:
        viewer.zoom_box.visible = True

    # on mouse press
    press_position = None
    if event.type == "mouse_press":
        press_position = event.position
        viewer.zoom_box.bounds = (press_position, press_position)
        # viewer.events.crosshair(position=event.position)
        yield

    # on mouse move
    while event.type == "mouse_move" and "Shift" in event.modifiers:
        if press_position is None:
            continue
        position = event.position
        viewer.zoom_box.bounds = (press_position, position)
        # viewer.events.crosshair(position=event.position)
        yield

    # on mouse release
    viewer.zoom_box.visible = False
    viewer.events.zoom(value=viewer.zoom_box.extents())
    yield
