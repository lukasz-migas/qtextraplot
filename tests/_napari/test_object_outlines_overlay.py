"""Tests for object outline overlays."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
vispy = pytest.importorskip("vispy", reason="vispy is not installed")

from napari.layers import Image  # noqa: E402
from qtpy.QtWidgets import QWidget  # noqa: E402

from qtextraplot._napari._vispy.overlays.object_outlines import outline_data_to_scene, points_to_segments  # noqa: E402
from qtextraplot._napari.component_controls.qt_object_outline_controls import QtObjectOutlineControls  # noqa: E402
from qtextraplot._napari.components.overlays.object_outlines import (  # noqa: E402
    ObjectOutlinesOverlay,
    normalize_object_outlines,
)
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar  # noqa: E402
from qtextraplot._napari.image.components.viewer_model import Viewer  # noqa: E402
from qtextraplot._napari.image.wrapper import NapariImageView  # noqa: E402


def test_normalize_single_outline_with_single_color_and_width():
    data = np.array([[0, 0], [1, 1], [2, 0]])

    outlines = normalize_object_outlines(data, color="green", width=2.5)

    assert len(outlines) == 1
    np.testing.assert_array_equal(outlines[0].data, data)
    np.testing.assert_allclose(outlines[0].color, [0, 0.50196078, 0, 1])
    assert outlines[0].width == 2.5


def test_normalize_multiple_outlines_with_per_outline_color_and_width():
    first = np.array([[0, 0], [1, 1], [2, 0]])
    second = np.array([[3, 3], [4, 4], [5, 3]])

    outlines = normalize_object_outlines([first, second], color=["red", "blue"], width=[1, 3])

    assert len(outlines) == 2
    np.testing.assert_allclose(outlines[0].color, [1, 0, 0, 1])
    np.testing.assert_allclose(outlines[1].color, [0, 0, 1, 1])
    assert [outline.width for outline in outlines] == [1, 3]


def test_normalize_multiple_outlines_broadcasts_single_color_and_width():
    first = np.array([[0, 0], [1, 1]])
    second = np.array([[3, 3], [4, 4]])

    outlines = normalize_object_outlines([first, second], color="yellow", width=4)

    assert len(outlines) == 2
    assert [outline.width for outline in outlines] == [4, 4]
    np.testing.assert_allclose(outlines[0].color, outlines[1].color)


def test_single_outline_rejects_multiple_colors():
    data = np.array([[0, 0], [1, 1], [2, 0]])

    with pytest.raises(ValueError, match="single outline"):
        normalize_object_outlines(data, color=["red", "blue"])


def test_multiple_outlines_rejects_color_count_mismatch():
    first = np.array([[0, 0], [1, 1]])
    second = np.array([[3, 3], [4, 4]])

    with pytest.raises(ValueError, match="Color count"):
        normalize_object_outlines([first, second], color=["red", "green", "blue"])


def test_width_validation():
    data = np.array([[0, 0], [1, 1]])

    with pytest.raises(ValueError, match="positive"):
        normalize_object_outlines(data, width=0)

    with pytest.raises(ValueError, match="single outline"):
        normalize_object_outlines(data, width=[1, 2])


def test_overlay_set_outlines_updates_model():
    data = np.array([[0, 0], [1, 1]])
    overlay = ObjectOutlinesOverlay()

    overlay.set_outlines(data, color="cyan", width=2)

    assert len(overlay.outlines) == 1
    assert overlay.outlines[0].width == 2


def test_overlay_constructor_accepts_outlines_color_and_width():
    first = np.array([[0, 0], [1, 1]])
    second = np.array([[2, 2], [3, 3]])

    overlay = ObjectOutlinesOverlay(outlines=[first, second], color=["red", "blue"], width=[2, 4])

    assert len(overlay.outlines) == 2
    assert [outline.width for outline in overlay.outlines] == [2, 4]
    np.testing.assert_allclose(overlay.outlines[1].color, [0, 0, 1, 1])


def test_points_to_open_and_closed_segments():
    points = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0]])

    open_segments = points_to_segments(points, closed=False)
    closed_segments = points_to_segments(points, closed=True)

    np.testing.assert_array_equal(
        open_segments,
        np.array([[0, 0, 0], [1, 0, 0], [1, 0, 0], [1, 1, 0]]),
    )
    np.testing.assert_array_equal(
        closed_segments,
        np.array([[0, 0, 0], [1, 0, 0], [1, 0, 0], [1, 1, 0], [1, 1, 0], [0, 0, 0]]),
    )


def test_outline_data_to_scene_uses_layer_data_transform():
    layer = Image(np.zeros((10, 10)), scale=(2, 3), translate=(5, 7))
    data = np.array([[1, 2], [3, 4]])

    scene = outline_data_to_scene(data, layer, displayed=(0, 1))

    np.testing.assert_allclose(scene, np.array([[13, 7, 0], [19, 11, 0]]))


def test_viewer_supports_multiple_named_object_outline_overlays():
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")

    first = viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="first", target_layer=image)
    second = viewer.set_object_outlines(np.array([[2, 2], [3, 3]]), name="second", target_layer=image)

    assert viewer._overlays["first"] is first
    assert viewer._overlays["second"] is second

    viewer.clear_object_outlines("first")

    assert "first" not in viewer._overlays
    assert viewer._overlays["second"] is second

    viewer.clear_object_outlines()

    assert "second" not in viewer._overlays


def test_viewer_sets_all_object_outline_visibility():
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")
    viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="first", target_layer=image)
    viewer.set_object_outlines(np.array([[2, 2], [3, 3]]), name="second", target_layer=image)

    assert viewer.object_outlines_visible

    viewer.set_object_outlines_visible(False)

    assert not viewer.object_outlines_visible
    assert not any(overlay.visible for overlay in viewer.object_outline_overlays().values())


def test_viewer_clear_canvas_removes_object_outline_overlays():
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")
    viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="first", target_layer=image)

    viewer.clear_canvas()

    assert "first" not in viewer._overlays


def test_object_outline_controls_update_selected_overlay(qtbot):
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")
    overlay = viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="Objects", target_layer=image)
    controls = QtObjectOutlineControls(viewer)
    qtbot.addWidget(controls)

    assert controls.overlay_combobox.count() == 1
    assert controls.overlay_combobox.currentData() == "Objects"

    controls.visible_checkbox.setChecked(False)
    controls.on_change_visible()
    controls.closed_checkbox.setChecked(False)
    controls.on_change_closed()
    controls.width_spinbox.setValue(4.0)
    controls.on_change_width()
    controls.on_change_color(np.array([0.0, 0.0, 1.0, 1.0]))

    assert not overlay.visible
    assert not overlay.closed
    assert overlay.outlines[0].width == 4.0
    np.testing.assert_allclose(overlay.outlines[0].color, [0, 0, 1, 1])


def test_object_outline_controls_clear_selected_overlay(qtbot):
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")
    viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="Objects", target_layer=image)
    controls = QtObjectOutlineControls(viewer)
    qtbot.addWidget(controls)

    controls.on_clear_selected_overlay()

    assert not viewer.object_outline_overlays()
    assert controls.overlay_combobox.count() == 0


def test_toolbar_object_outline_button_toggles_visibility(qtbot):
    viewer = Viewer()
    image = viewer.add_image(np.zeros((10, 10)), name="Target")
    overlay = viewer.set_object_outlines(np.array([[0, 0], [1, 1]]), name="Objects", target_layer=image)
    qt_viewer = QWidget()
    qt_viewer.viewer = viewer
    qt_viewer.on_toggle_controls_dialog = lambda: None
    qtbot.addWidget(qt_viewer)
    toolbar = QtViewToolbar(view=None, viewer=viewer, qt_viewer=qt_viewer, allow_crosshair=False)
    qtbot.addWidget(toolbar)

    assert toolbar.tools_object_outlines_btn.isChecked()

    toolbar._toggle_object_outlines_visible(False)

    assert not overlay.visible
    assert not toolbar.tools_object_outlines_btn.isChecked()


def test_image_view_exposes_object_outline_api():
    signature = inspect.signature(NapariImageView.set_object_outlines)

    assert "outlines" in signature.parameters
    assert "color" in signature.parameters
    assert "width" in signature.parameters
