"""Regression tests for embedded napari text overlays."""

from __future__ import annotations

import typing as ty

import numpy as np
import pytest
from napari_plot.components.viewer_model import ViewerModel

from qtextraplot._napari.component_controls.qt_text_overlay_controls import QtTextOverlayControls
from qtextraplot._napari.image.wrapper import NapariImageView
from qtextraplot._napari.line.wrapper import NapariLineView


def _text_visual(view: NapariImageView | NapariLineView) -> ty.Any:
    """Return the single VisPy visual for the viewer text overlay."""
    visual = view.widget.canvas._overlay_to_visual[view.viewer.text_overlay]
    return visual[0] if isinstance(visual, list) else visual


def test_text_overlay_controls_update_box_style(qtbot: ty.Any) -> None:
    """The text controls should edit and track the background box style."""
    viewer = ViewerModel()
    viewer.text_overlay.visible = True
    controls = QtTextOverlayControls(viewer)
    qtbot.addWidget(controls)

    assert controls.box_checkbox.isChecked()
    assert controls.box_color_swatch.isEnabled()

    controls.box_checkbox.setChecked(False)
    assert viewer.text_overlay.box is False
    assert not controls.box_color_swatch.isEnabled()

    controls.box_checkbox.setChecked(True)
    controls.box_color_swatch.setColor("red")
    assert viewer.text_overlay.box is True
    np.testing.assert_allclose(viewer.text_overlay.box_color, [1, 0, 0, 1])

    viewer.text_overlay.box = False
    viewer.text_overlay.box_color = "blue"
    assert not controls.box_checkbox.isChecked()
    np.testing.assert_allclose(controls.box_color_swatch.color, [0, 0, 1, 1])


@pytest.mark.parametrize(
    ("view_class", "kwargs"),
    [
        pytest.param(
            NapariImageView,
            {"add_dims": False, "add_toolbars": False, "allow_extraction": False},
            id="image",
        ),
        pytest.param(
            NapariLineView,
            {"add_toolbars": False, "connect_theme": False},
            id="line",
        ),
    ],
)
def test_text_overlay_background_uses_text_geometry(
    qtbot: ty.Any,
    _mock_opengl_capabilities: None,
    view_class: type[NapariImageView | NapariLineView],
    kwargs: dict[str, ty.Any],
) -> None:
    """Both embedded viewers should display a full text-sized background."""
    view = view_class(**kwargs)
    qtbot.addWidget(view.widget)
    overlay = view.viewer.text_overlay
    overlay.text = "testing some text"
    overlay.visible = True
    visual = _text_visual(view)
    qtbot.waitUntil(lambda: visual.x_size > 0 and visual.y_size > 0)

    assert overlay.box is True
    assert visual.box.parent is visual.node.parent
    assert visual.box.width > visual.x_size
    assert visual.box.height > visual.y_size
