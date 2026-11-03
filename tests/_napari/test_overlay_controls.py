"""Tests for the napari 0.10 overlay controls (axes, cursor crosshair, coordinate grid)."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from qtpy.QtWidgets import QWidget

napari = pytest.importorskip("napari", reason="napari is not installed")

from napari.components._viewer_constants import CanvasPosition  # noqa: E402

from qtextraplot._napari.component_controls.qt_axes_controls import QtAxesControls  # noqa: E402
from qtextraplot._napari.component_controls.qt_coordinate_grid_controls import (  # noqa: E402
    QtCoordinateGridControls,
)
from qtextraplot._napari.component_controls.qt_crosshair_controls import QtCrosshairControls  # noqa: E402
from qtextraplot._napari.component_controls.qt_cursor_crosshair_controls import (  # noqa: E402
    QtCursorCrosshairControls,
)
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar  # noqa: E402
from qtextraplot._napari.image.components.viewer_model import Viewer  # noqa: E402
from qtextraplot._napari.widgets.qt_font_size import QtFontSizeWidget, default_font_size  # noqa: E402
from qtextraplot._napari.widgets.qt_optional_color import QtOptionalColorWidget  # noqa: E402


def _toolbar(qtbot, viewer: Viewer) -> QtViewToolbar:
    qt_viewer = QWidget()
    qt_viewer.viewer = viewer
    qt_viewer.on_toggle_controls_dialog = lambda: None
    qtbot.addWidget(qt_viewer)
    toolbar = QtViewToolbar(view=None, viewer=viewer, qt_viewer=qt_viewer)
    qtbot.addWidget(toolbar)
    toolbar.connect_toolbar()
    return toolbar


def test_font_size_widget_supports_auto(qtbot) -> None:
    values = []
    widget = QtFontSizeWidget(value=None, func=values.append)
    qtbot.addWidget(widget)

    assert widget.value() is None
    assert widget.slider.value() == default_font_size()
    assert not widget.slider.isEnabled()

    widget.auto_checkbox.setChecked(False)
    widget.slider.setValue(14)
    assert widget.value() == 14
    assert values[-1] == 14

    widget.setValue(None)
    assert widget.value() is None
    assert values[-1] is None


def test_optional_color_widget_supports_auto(qtbot) -> None:
    values = []
    widget = QtOptionalColorWidget(value=None, func=values.append)
    qtbot.addWidget(widget)

    assert widget.value() is None
    widget.auto_checkbox.setChecked(False)
    widget.color_swatch.setColor("red")
    np.testing.assert_allclose(widget.value(), [1, 0, 0, 1])
    np.testing.assert_allclose(values[-1], [1, 0, 0, 1])

    widget.setValue(None)
    assert widget.value() is None
    assert not widget.color_swatch.isEnabled()


def test_axes_controls_sync_scene_and_canvas_axes(qtbot) -> None:
    viewer = Viewer()
    controls = QtAxesControls(viewer)
    qtbot.addWidget(controls)
    scene_axes = viewer.scene.overlays.axes
    canvas_axes = viewer.canvas.overlays.axes

    # widgets -> model
    controls.scene_visible_checkbox.setChecked(True)
    controls.scene_widgets["dashed"].setChecked(True)
    controls.scene_widgets["font_size"].setValue(15)
    assert scene_axes.visible
    assert scene_axes.dashed
    assert scene_axes.font_size == 15
    assert not canvas_axes.visible

    controls.canvas_visible_checkbox.setChecked(True)
    controls.canvas_widgets["arrows"].setChecked(False)
    controls.canvas_widgets["size"].setValue(150)
    position = controls.canvas_widgets["position"]
    position.setCurrentIndex(position.findData(CanvasPosition.TOP_RIGHT))
    controls.canvas_widgets["box_color"].auto_checkbox.setChecked(False)
    controls.canvas_widgets["box_color"].color_swatch.setColor("red")
    assert canvas_axes.visible
    assert not canvas_axes.arrows
    assert canvas_axes.size == 150
    assert canvas_axes.position == CanvasPosition.TOP_RIGHT
    np.testing.assert_allclose(canvas_axes.box_color, [1, 0, 0, 1])

    # model -> widgets
    scene_axes.labels = False
    scene_axes.font_size = None
    canvas_axes.box_color = None
    canvas_axes.visible = False
    assert not controls.scene_widgets["labels"].isChecked()
    assert controls.scene_widgets["font_size"].value() is None
    assert controls.canvas_widgets["box_color"].value() is None
    assert not controls.canvas_visible_checkbox.isChecked()
    assert not controls.canvas_widgets["size"].isEnabled()


def test_cursor_crosshair_controls_sync(qtbot) -> None:
    viewer = Viewer()
    controls = QtCursorCrosshairControls(viewer)
    qtbot.addWidget(controls)
    overlay = viewer.scene.overlays.crosshair

    assert not controls.gap_slider.isEnabled()
    controls.visible_checkbox.setChecked(True)
    assert overlay.visible
    assert controls.gap_slider.isEnabled()

    controls.gap_slider.setValue(35)
    controls.opacity_slider.setValue(0.5)
    controls.color_widget.auto_checkbox.setChecked(False)
    controls.color_widget.color_swatch.setColor("lime")
    assert overlay.gap == 35
    assert overlay.opacity == 0.5
    np.testing.assert_allclose(overlay.color, [0, 1, 0, 1])

    overlay.color = None
    overlay.gap = 5
    assert controls.color_widget.value() is None
    assert controls.gap_slider.value() == 5


def test_coordinate_grid_controls_sync(qtbot) -> None:
    viewer = Viewer()
    controls = QtCoordinateGridControls(viewer)
    qtbot.addWidget(controls)
    overlay = viewer.scene.overlays.coordinate_grid

    controls.visible_checkbox.setChecked(True)
    controls.tick_labels_checkbox.setChecked(False)
    controls.n_ticks_slider.setValue(8)
    controls.font_size_widget.setValue(12)
    assert overlay.visible
    assert not overlay.tick_labels
    assert overlay.n_ticks == 8
    assert overlay.font_size == 12

    overlay.axis_labels = False
    overlay.n_ticks = 3
    assert not controls.axis_labels_checkbox.isChecked()
    assert controls.n_ticks_slider.value() == 3


@pytest.mark.parametrize("controls_class", [QtAxesControls, QtCursorCrosshairControls, QtCoordinateGridControls])
def test_overlay_controls_disconnect_on_close(qtbot, controls_class) -> None:
    viewer = Viewer()
    overlay_events = [
        viewer.scene.overlays.axes.events.visible,
        viewer.canvas.overlays.axes.events.visible,
        viewer.scene.overlays.crosshair.events.visible,
        viewer.scene.overlays.coordinate_grid.events.visible,
    ]
    n_callbacks = [len(emitter) for emitter in overlay_events]

    controls = controls_class(viewer)
    qtbot.addWidget(controls)
    assert [len(emitter) for emitter in overlay_events] != n_callbacks

    controls.close()
    assert [len(emitter) for emitter in overlay_events] == n_callbacks


def test_toolbar_toggles_new_overlays(qtbot) -> None:
    viewer = Viewer()
    toolbar = _toolbar(qtbot, viewer)

    toolbar._toggle_cursor_crosshair_visible(True)
    toolbar._toggle_coordinate_grid_visible(True)
    toolbar._toggle_axes_visible(True)
    assert viewer.scene.overlays.crosshair.visible
    assert viewer.scene.overlays.coordinate_grid.visible
    assert viewer.scene.overlays.axes.visible

    viewer.scene.overlays.crosshair.visible = False
    assert not toolbar.tools_cursor_crosshair_btn.isChecked()
    assert toolbar.tools_coordinate_grid_btn.isChecked()

    # the axes button reflects either axes overlay and hides both
    viewer.scene.overlays.axes.visible = False
    viewer.canvas.overlays.axes.visible = True
    assert toolbar.tools_axes_btn.isChecked()
    toolbar._toggle_axes_visible(False)
    assert not viewer.canvas.overlays.axes.visible
    assert not toolbar.tools_axes_btn.isChecked()


def test_crosshair_controls_sync(qtbot) -> None:
    viewer = Viewer()
    controls = QtCrosshairControls(viewer)
    qtbot.addWidget(controls)

    controls.width_spinbox.setValue(4)
    controls.position_x_spin.setValue(12)
    controls.position_y_spin.setValue(7)
    assert viewer.cross_hair.width == 4
    assert tuple(viewer.cross_hair.position) == (7, 12)

    viewer.cross_hair.window = 6
    assert controls.window_spinbox.value() == 6
    controls.close()


def test_viewers_do_not_use_deprecated_napari_api(qtbot, _mock_opengl_capabilities) -> None:
    """Constructing both viewers should not touch napari's deprecated viewer attributes."""
    from qtextraplot._napari.image.wrapper import NapariImageView

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        image_view = NapariImageView(add_dims=False)
        qtbot.addWidget(image_view.widget)
        image_view.add_image(np.zeros((4, 4)))
        image_view.widget.viewerToolbar.on_open_axes_config()

    pytest.importorskip("napari_plot", reason="napari-plot is not installed")
    from qtextraplot._napari.line.wrapper import NapariLineView

    parent = QWidget()
    qtbot.addWidget(parent)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        line_view = NapariLineView(parent)
        line_view.plot(np.arange(5), np.arange(5))
