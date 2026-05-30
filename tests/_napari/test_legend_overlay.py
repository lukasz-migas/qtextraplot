"""Tests for legend overlays."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
vispy = pytest.importorskip("vispy", reason="vispy is not installed")

from napari._vispy.utils.visual import overlay_to_visual  # noqa: E402
from qtpy.QtWidgets import QWidget  # noqa: E402

from qtextraplot._napari._vispy import register_vispy_overlays  # noqa: E402
from qtextraplot._napari._vispy.overlays.legend import VispyLegendOverlay, legend_layout_size  # noqa: E402
from qtextraplot._napari.component_controls.qt_legend_controls import QtLegendControls  # noqa: E402
from qtextraplot._napari.components.overlays.legend import (  # noqa: E402
    LegendEntry,
    LegendOverlay,
    legend_entries_from_points,
)
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar  # noqa: E402
from qtextraplot._napari.image.components.viewer_model import Viewer  # noqa: E402
from qtextraplot._napari.image.wrapper import NapariImageView  # noqa: E402


def test_legend_entry_validates_single_color():
    entry = LegendEntry(label="cell", marker="o", color="red")

    assert entry.label == "cell"
    assert entry.marker == "disc"
    np.testing.assert_allclose(entry.color, [1, 0, 0, 1])


def test_legend_entry_rejects_multiple_colors():
    with pytest.raises(ValueError, match="single color"):
        LegendEntry(label="cell", color=["red", "blue"])


def test_legend_overlay_validates_style_values():
    with pytest.raises(ValueError, match="positive"):
        LegendOverlay(entries=[{"label": "cell"}], font_size=0)

    with pytest.raises(ValueError, match="non-negative"):
        LegendOverlay(entries=[{"label": "cell"}], border_width=-1)


def test_legend_overlay_accepts_sequence_of_entries():
    overlay = LegendOverlay(
        entries=[
            {"label": "cell", "marker": "disc", "color": "cyan"},
            LegendEntry(label="nucleus", marker="square", color="yellow"),
        ],
        visible=True,
        position="bottom_left",
    )

    assert overlay.visible
    assert str(overlay.position) == "bottom_left"
    assert [entry.label for entry in overlay.entries] == ["cell", "nucleus"]
    np.testing.assert_allclose(overlay.entries[0].color, [0, 1, 1, 1])


def test_legend_entries_from_points_keeps_distinct_styles_for_duplicate_labels():
    viewer = Viewer()
    points = viewer.add_points(
        np.asarray([[0, 0], [1, 1], [2, 2]]),
        properties={"label": np.asarray(["cell", "cell", "nucleus"])},
        face_color=["red", "blue", "green"],
        symbol=["disc", "square", "diamond"],
    )

    entries = legend_entries_from_points(points)

    assert [entry.label for entry in entries] == ["cell", "cell", "nucleus"]
    assert [entry.marker for entry in entries] == ["disc", "square", "diamond"]
    np.testing.assert_allclose(entries[0].color, [1, 0, 0, 1])
    np.testing.assert_allclose(entries[1].color, [0, 0, 1, 1])
    np.testing.assert_allclose(entries[2].color, [0, 0.50196078, 0, 1])


def test_legend_entries_from_points_can_collapse_duplicate_labels():
    viewer = Viewer()
    points = viewer.add_points(
        np.asarray([[0, 0], [1, 1], [2, 2]]),
        properties={"label": np.asarray(["cell", "cell", "nucleus"])},
        face_color=["red", "blue", "green"],
        symbol=["disc", "square", "diamond"],
    )

    entries = legend_entries_from_points(points, group_by_style=False)

    assert [entry.label for entry in entries] == ["cell", "nucleus"]
    assert [entry.marker for entry in entries] == ["disc", "diamond"]


def test_viewer_supports_named_legend_overlays():
    viewer = Viewer()
    first = viewer.set_legend([{"label": "A", "color": "red"}], name="first")
    second = viewer.set_legend([{"label": "B", "color": "blue"}], name="second")

    assert viewer._overlays["first"] is first
    assert viewer._overlays["second"] is second
    assert viewer.legend_visible

    viewer.set_legend_visible(False)

    assert not viewer.legend_visible
    assert not first.visible
    assert not second.visible

    viewer.clear_legend("first")

    assert "first" not in viewer._overlays
    assert viewer._overlays["second"] is second


def test_viewer_sets_legend_from_points_layer_name():
    viewer = Viewer()
    viewer.add_points(
        np.asarray([[0, 0], [1, 1]]),
        name="Objects",
        properties={"label": np.asarray(["A", "B"])},
        face_color=["red", "blue"],
    )

    overlay = viewer.set_legend_from_points("Objects")

    assert [entry.label for entry in overlay.entries] == ["A", "B"]
    np.testing.assert_allclose(overlay.entries[1].color, [0, 0, 1, 1])


def test_viewer_refreshes_point_legend_from_source():
    viewer = Viewer()
    points = viewer.add_points(
        np.asarray([[0, 0]]),
        name="Objects",
        properties={"label": np.asarray(["A"])},
        face_color=["red"],
        symbol=["disc"],
    )
    overlay = viewer.set_legend_from_points(points)

    points.data = np.asarray([[0, 0], [1, 1]])
    points.face_color = ["red", "blue"]
    points.symbol = ["disc", "square"]
    viewer.refresh_legend_from_source()

    assert [entry.label for entry in overlay.entries] == ["A", "A"]
    assert [entry.marker for entry in overlay.entries] == ["disc", "square"]
    np.testing.assert_allclose(overlay.entries[1].color, [0, 0, 1, 1])


def test_viewer_auto_syncs_point_legend_source():
    viewer = Viewer()
    points = viewer.add_points(
        np.asarray([[0, 0]]),
        name="Objects",
        properties={"label": np.asarray(["A"])},
        face_color=["red"],
        symbol=["disc"],
    )
    overlay = viewer.set_legend_from_points(points, sync=True)

    points.face_color = ["blue"]
    points.symbol = ["square"]

    assert overlay.sync_with_source
    assert overlay.entries[0].marker == "square"
    np.testing.assert_allclose(overlay.entries[0].color, [0, 0, 1, 1])


def test_vispy_legend_overlay_registration_and_size():
    register_vispy_overlays()
    assert overlay_to_visual[LegendOverlay] is VispyLegendOverlay

    viewer = Viewer()
    overlay = viewer.set_legend([{"label": "Cell", "marker": "disc", "color": "red"}])
    visual = VispyLegendOverlay(viewer, overlay)

    assert legend_layout_size(overlay) == (visual.x_size, visual.y_size)
    assert visual.x_size > 0
    assert visual.y_size > 0

    visual.close()


def test_vispy_legend_position_change_requests_canvas_update():
    viewer = Viewer()
    overlay = viewer.set_legend([{"label": "Long legend label", "marker": "disc", "color": "red"}])
    visual = VispyLegendOverlay(viewer, overlay)
    calls = []
    visual.canvas_position_callback = lambda: calls.append(True)

    overlay.position = "bottom_left"

    assert calls
    assert visual.x_size > (len("Long legend label") * overlay.font_size * 0.6)

    visual.close()


def test_legend_controls_generate_from_points_and_update_style(qtbot):
    viewer = Viewer()
    points = viewer.add_points(
        np.asarray([[0, 0], [1, 1]]),
        name="Objects",
        properties={"label": np.asarray(["A", "B"])},
        face_color=["red", "blue"],
    )
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)

    assert controls.source_layer_combobox.currentData() is points

    controls.on_generate_from_points()
    overlay = viewer._overlays["Legend"]

    assert isinstance(overlay, LegendOverlay)
    assert [entry.label for entry in overlay.entries] == ["A", "B"]
    assert overlay.source_layer == "Objects"

    controls.visible_checkbox.setChecked(False)
    controls.on_change_visible()
    controls.font_size_spinbox.setValue(18)
    controls.on_change_font_size()
    controls.marker_size_spinbox.setValue(16)
    controls.on_change_marker_size()
    controls.on_change_text_color(np.asarray([0.0, 1.0, 0.0, 1.0]))

    assert not overlay.visible
    assert overlay.font_size == 18
    assert overlay.marker_size == 16
    np.testing.assert_allclose(overlay.text_color, [0, 1, 0, 1])

    points.face_color = ["green", "blue"]
    controls.on_generate_from_points()

    np.testing.assert_allclose(overlay.entries[0].color, [0, 0.50196078, 0, 1])
    assert overlay.font_size == 18


def test_legend_controls_toggle_auto_sync(qtbot):
    viewer = Viewer()
    viewer.add_points(
        np.asarray([[0, 0]]),
        name="Objects",
        properties={"label": np.asarray(["A"])},
        face_color=["red"],
    )
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)
    controls.on_generate_from_points()

    controls.auto_sync_checkbox.setChecked(True)
    controls.on_change_auto_sync()

    overlay = viewer._overlays["Legend"]
    assert overlay.sync_with_source


def test_legend_controls_clear_selected_overlay(qtbot):
    viewer = Viewer()
    viewer.set_legend([{"label": "A"}], name="Objects")
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)

    controls.on_clear_selected_overlay()

    assert not viewer.legend_overlays()
    assert controls.overlay_combobox.count() == 0


def test_toolbar_legend_button_toggles_visibility(qtbot):
    viewer = Viewer()
    overlay = viewer.set_legend([{"label": "A"}], name="Objects")
    qt_viewer = QWidget()
    qt_viewer.viewer = viewer
    qt_viewer.on_toggle_controls_dialog = lambda: None
    qtbot.addWidget(qt_viewer)
    toolbar = QtViewToolbar(
        view=None,
        viewer=viewer,
        qt_viewer=qt_viewer,
        allow_crosshair=False,
        allow_object_outlines=False,
    )
    qtbot.addWidget(toolbar)

    assert toolbar.tools_legend_btn.isChecked()

    toolbar._toggle_legend_visible(False)

    assert not overlay.visible
    assert not toolbar.tools_legend_btn.isChecked()


def test_image_view_exposes_legend_api():
    signature = inspect.signature(NapariImageView.set_legend)

    assert "entries" in signature.parameters
    assert "position" in signature.parameters
    assert "text_color" in signature.parameters
    assert "marker_size" in signature.parameters
    assert hasattr(NapariImageView, "set_legend_from_points")
    assert hasattr(NapariImageView, "clear_legend")
    assert hasattr(NapariImageView, "refresh_legend_from_source")
