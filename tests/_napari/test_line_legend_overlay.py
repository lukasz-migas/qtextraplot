"""Tests for napari-plot line legend overlays."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("napari_plot", reason="napari-plot is not installed")

from qtpy.QtCore import QPoint, Qt  # noqa: E402
from qtpy.QtWidgets import QWidget  # noqa: E402

from qtextraplot._napari._constants import CanvasPosition  # noqa: E402
from qtextraplot._napari.component_controls.qt_legend_controls import QtLegendControls  # noqa: E402
from qtextraplot._napari.components.overlays.legend import LegendOverlay  # noqa: E402
from qtextraplot._napari.line._vispy.canvas import CANVAS_OVERLAY_PADDING  # noqa: E402
from qtextraplot._napari.line.component_controls.qt_view_toolbar import QtViewRightToolbar  # noqa: E402
from qtextraplot._napari.line.components.viewer_model import (  # noqa: E402
    LEGEND_OVERLAY_NAME,
    Viewer,
    legend_entries_from_layers,
)
from qtextraplot._napari.line.wrapper import NapariLineView  # noqa: E402


def test_line_legend_entries_from_supported_layers() -> None:
    """Supported line-viewer layers should create one legend row each."""
    viewer = Viewer()
    line = viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="Line", color="red", width=3)
    centroids = viewer.add_centroids(
        np.asarray([[0, 1], [1, 2]]),
        name="Centroids",
        color=["cyan", "yellow"],
        orientation="horizontal",
        width=5,
    )
    scatter = viewer.add_scatter(
        np.asarray([[0, 0], [1, 1]]),
        name="Scatter",
        face_color=["blue", "green"],
        border_color=["red", "yellow"],
        symbol=["square", "diamond"],
    )
    points = viewer.add_points(
        np.asarray([[0, 0], [1, 1]]),
        name="Points",
        face_color="magenta",
        symbol="triangle_up",
    )

    entries = legend_entries_from_layers([line, centroids, scatter, points])

    assert [entry.label for entry in entries] == ["Line", "Centroids", "Scatter", "Points"]
    assert [entry.marker for entry in entries] == ["hbar", "hbar", "square", "triangle_up"]
    np.testing.assert_allclose(entries[0].color, [1, 0, 0, 1])
    np.testing.assert_allclose(entries[1].color, [0, 1, 1, 1])
    np.testing.assert_allclose(entries[2].color, [0, 0, 1, 1])
    np.testing.assert_allclose(entries[3].color, [1, 0, 1, 1])


def test_line_legend_entries_skip_hidden_empty_and_unsupported_layers() -> None:
    """Automatic line legends should include only visible supported layers with data."""
    viewer = Viewer()
    visible = viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="Visible", color="red")
    viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="Hidden", visible=False)
    viewer.add_line(np.empty((0, 2)), name="Empty")
    viewer.add_shapes(
        data=[np.asarray([[0, 0], [1, 0], [1, 1], [0, 1]])],
        shape_type=["polygon"],
        name="Shape",
    )

    entries = legend_entries_from_layers(viewer.layers)

    assert [entry.label for entry in entries] == [visible.name]


def test_line_viewer_auto_refreshes_default_layer_legend() -> None:
    """The default line legend should remain hidden but sync with layer changes."""
    viewer = Viewer()
    overlay = viewer._overlays[LEGEND_OVERLAY_NAME]

    assert isinstance(overlay, LegendOverlay)
    assert not overlay.visible
    assert overlay.sync_with_source
    assert not overlay.entries

    line = viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="Line", color="red")

    assert [entry.label for entry in overlay.entries] == ["Line"]
    np.testing.assert_allclose(overlay.entries[0].color, [1, 0, 0, 1])

    line.color = "blue"
    line.name = "Renamed"

    assert [entry.label for entry in overlay.entries] == ["Renamed"]
    np.testing.assert_allclose(overlay.entries[0].color, [0, 0, 1, 1])

    line.visible = False
    assert not overlay.entries

    line.visible = True
    assert [entry.label for entry in overlay.entries] == ["Renamed"]

    viewer.layers.remove(line)
    assert not overlay.entries


def test_line_viewer_auto_legend_tracks_layer_reorder() -> None:
    """Layer-derived legend rows should follow layer order."""
    viewer = Viewer()
    first = viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="First", color="red")
    second = viewer.add_line(np.asarray([[0, 0], [1, 2]]), name="Second", color="blue")
    overlay = viewer._overlays[LEGEND_OVERLAY_NAME]

    assert [entry.label for entry in overlay.entries] == ["First", "Second"]

    viewer.layers.move(viewer.layers.index(second), viewer.layers.index(first))

    assert [entry.label for entry in overlay.entries] == ["Second", "First"]


def test_line_toolbar_legend_button_toggles_visibility(qtbot) -> None:
    """The line toolbar legend button should control legend visibility."""
    viewer = Viewer()

    class DummyQtViewer(QWidget):
        """Small Qt viewer stand-in for toolbar tests."""

        def __init__(self) -> None:
            super().__init__()
            self.viewer = viewer

        def on_toggle_controls_dialog(self) -> None:
            """No-op layer controls toggle."""

        def clipboard(self) -> None:
            """No-op clipboard action."""

        def on_save_figure(self) -> None:
            """No-op save action."""

    qt_viewer = DummyQtViewer()
    view = QWidget()
    qtbot.addWidget(qt_viewer)
    qtbot.addWidget(view)
    toolbar = QtViewRightToolbar(view=view, viewer=viewer, qt_viewer=qt_viewer)
    qtbot.addWidget(toolbar)

    overlay = viewer._overlays[LEGEND_OVERLAY_NAME]
    assert not overlay.visible
    assert not toolbar.tools_legend_btn.isChecked()

    toolbar._toggle_legend_visible(True)

    assert overlay.visible
    assert toolbar.tools_legend_btn.isChecked()


def test_line_view_exposes_legend_api() -> None:
    """NapariLineView should expose line legend helpers."""
    signature = inspect.signature(NapariLineView.set_legend)

    assert "entries" in signature.parameters
    assert hasattr(NapariLineView, "set_legend_from_layers")
    assert hasattr(NapariLineView, "refresh_legend_from_layers")
    assert hasattr(NapariLineView, "clear_legend")


def test_line_legend_controls_generate_from_layers_without_label_property(qtbot) -> None:
    """Line controls should derive legend rows from layers rather than point features."""
    viewer = Viewer()
    viewer.add_line(np.asarray([[0, 0], [1, 1]]), name="Line", color="red")
    viewer.add_points(
        np.asarray([[0, 0], [1, 1]]),
        name="Points",
        face_color="blue",
        symbol="square",
    )
    overlay = viewer.set_legend_from_layers(
        visible=True,
        sync=False,
        position=CanvasPosition.BOTTOM_LEFT,
        font_size=17,
    )
    controls = QtLegendControls(viewer)
    qtbot.addWidget(controls)

    assert controls.generate_button.text() == "From layers"

    controls.auto_sync_checkbox.setChecked(True)
    controls.on_generate_from_layers()

    assert viewer._overlays[LEGEND_OVERLAY_NAME] is overlay
    assert [entry.label for entry in overlay.entries] == ["Line", "Points"]
    assert overlay.source_layer is None
    assert overlay.sync_with_source
    assert overlay.position == CanvasPosition.BOTTOM_LEFT
    assert overlay.font_size == 17

    position_index = controls.position_combobox.findData(CanvasPosition.TOP_CENTER)
    controls.position_combobox.setCurrentIndex(position_index)
    controls.on_change_position()

    assert overlay.position == CanvasPosition.TOP_CENTER


def test_line_canvas_positions_and_resizes_legend(qtbot) -> None:
    """Line canvas should honor every legend position and updated legend dimensions."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False)
    qtbot.addWidget(view.widget)
    view.widget.resize(640, 480)
    view.widget.show()
    view.plot([0.0, 1.0], [0.0, 1.0], name="Line", color="red")
    overlay = view.set_legend_from_layers(visible=True, position=CanvasPosition.TOP_RIGHT)
    canvas = view.widget.canvas
    visual = canvas._overlay_to_visual[overlay]
    canvas._request_canvas_update()

    def expected_translation(position: CanvasPosition) -> tuple[float, float]:
        x_max, y_max = canvas.view.size
        if position in (CanvasPosition.TOP_LEFT, CanvasPosition.BOTTOM_LEFT):
            x = CANVAS_OVERLAY_PADDING
        elif position in (CanvasPosition.TOP_RIGHT, CanvasPosition.BOTTOM_RIGHT):
            x = x_max - visual.x_size - CANVAS_OVERLAY_PADDING
        else:
            x = (x_max - visual.x_size) / 2

        if position in (CanvasPosition.TOP_LEFT, CanvasPosition.TOP_CENTER, CanvasPosition.TOP_RIGHT):
            y = CANVAS_OVERLAY_PADDING
        else:
            y = y_max - visual.y_size - CANVAS_OVERLAY_PADDING
        return x, y

    for position in CanvasPosition:
        overlay.position = position
        np.testing.assert_allclose(visual.node.transform.translate[:2], expected_translation(position))

    overlay.position = CanvasPosition.TOP_RIGHT
    previous_width = visual.x_size
    overlay.font_size = 20

    assert visual.x_size > previous_width
    np.testing.assert_allclose(
        visual.node.transform.translate[:2],
        expected_translation(CanvasPosition.TOP_RIGHT),
    )

    x_max, y_max = canvas.view.size
    canvas.view.size = (x_max + 100, y_max + 50)
    canvas.on_resize(None)

    np.testing.assert_allclose(
        visual.node.transform.translate[:2],
        expected_translation(CanvasPosition.TOP_RIGHT),
    )


def test_line_view_reuses_scatter_and_applies_per_point_colors(qtbot) -> None:
    """Scatter updates should retain the layer and propagate point colors."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False)
    qtbot.addWidget(view.widget)

    layer = view.add_scatter([1.0, 2.0], [3.0, 4.0], name="points", color=["red", "blue"], symbol="o")
    updated = view.add_scatter([2.0], [5.0], name="points", color=["green"], symbol="s")

    assert updated is layer
    np.testing.assert_allclose(layer.face_color, [[0.0, 0.5019608, 0.0, 1.0]])
    np.testing.assert_allclose(layer.border_color, [[0.0, 0.5019608, 0.0, 1.0]])
    assert layer.symbol.tolist() == ["square"]


@pytest.mark.xfail(reason="flaky")
def test_line_view_forwards_modified_double_clicks(qtbot) -> None:
    """Ctrl-double-click should reach viewer callbacks with world coordinates."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False)
    qtbot.addWidget(view.widget)
    view.widget.resize(400, 300)
    view.widget.show()
    received: list[tuple[float, ...]] = []

    def on_double_click(_viewer: object, event: object) -> None:
        """Record the callback's world coordinate."""
        received.append(tuple(event.position))  # type: ignore[attr-defined]

    view.viewer.mouse_double_click_callbacks.append(on_double_click)

    qtbot.mouseDClick(
        view.widget.canvas.native,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier,
        pos=QPoint(200, 150),
    )

    assert len(received) == 1
