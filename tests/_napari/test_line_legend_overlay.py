"""Tests for napari-plot line legend overlays."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("napari_plot", reason="napari-plot is not installed")

from qtpy.QtWidgets import QWidget  # noqa: E402

from qtextraplot._napari.components.overlays.legend import LegendOverlay  # noqa: E402
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
