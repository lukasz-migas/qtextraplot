"""Tests for pyqtgraph-backed views."""

from __future__ import annotations

import numpy as np
import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QWidget

from qtextraplot.config import CANVAS

pg = pytest.importorskip("pyqtgraph")

from qtextraplot._pyqtgraph import (  # noqa: E402
    LegendEntry,
    ViewPyQtGraphCanvas,
    ViewPyQtGraphImage,
    ViewPyQtGraphLine,
    ViewPyQtGraphScatter,
)


def test_line_view_supports_lines_and_annotations(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphLine(parent, x_label="x", y_label="y")
    qtbot.addWidget(view.widget)

    view.plot(np.arange(5), np.arange(5), color="r")
    view.add_line(np.arange(5), np.arange(5) * 2, gid="other", color="g")
    view.add_vline(2, gid="vref")
    view.add_hline(3)
    patch = view.show_patch(1, 1, 2, 3, obj_name="roi")
    view.update_patch("roi", x=2, width=4)

    assert "__base__" in view.figure._plot_items
    assert "other" in view.figure._plot_items
    assert "vref" in view.figure._annotation_items
    assert "ax_hline" in view.figure._annotation_items
    assert patch is view.figure.get_existing_patch("roi")
    assert view.figure.get_existing_patch("roi").item.rect().x() == 2
    assert view.figure.get_existing_patch("roi").item.rect().width() == 4


def test_scatter_view_updates_data(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphScatter(parent)
    qtbot.addWidget(view.widget)

    view.plot(np.arange(3), np.arange(3), color="y", size=7)
    view.update(np.arange(4), np.arange(4) + 1, size=9)

    item = view.figure._plot_items["__scatter__"]
    assert isinstance(item, pg.ScatterPlotItem)
    data = item.getData()
    assert len(data[0]) == 4


def test_image_view_supports_image_and_overlaid_annotation(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphImage(parent)
    qtbot.addWidget(view.widget)

    image = np.arange(16).reshape(4, 4)
    view.plot(image)
    view.add_vline(1.5, gid="cursor")
    view.update(image + 1)

    item = view.figure._plot_items["__image__"]
    assert isinstance(item, pg.ImageItem)
    assert item.image.shape == image.T.shape
    assert "cursor" in view.figure._annotation_items


def test_universal_canvas_supports_mixed_items_and_reset(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphCanvas(parent, x_label="x", y_label="y")
    qtbot.addWidget(view.widget)

    line_x = np.arange(5)
    line_y = line_x * 2
    image = np.arange(16).reshape(4, 4)

    view.plot(line_x, line_y, gid="signal", color="r")
    view.scatter(line_x, line_x + 1, gid="points", color="y", size=8)
    view.imshow(image, gid="image", opacity=0.5)
    view.add_vline(2, gid="cursor")
    view.add_hline(1, gid="baseline")

    assert {"signal", "points", "image"} <= set(view.figure._plot_items)
    assert {"cursor", "baseline"} <= set(view.figure._annotation_items)

    view.reset()

    assert {"signal", "points", "image"} <= set(view.figure._plot_items)
    assert {"cursor", "baseline"} <= set(view.figure._annotation_items)

    view.clear()

    assert not view.figure._plot_items
    assert not view.figure._annotation_items


def test_universal_canvas_reuses_items_and_supports_per_point_colors(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphCanvas(parent)
    qtbot.addWidget(view.widget)

    view.plot(np.arange(3), np.arange(3), gid="signal")
    line = view.figure._plot_items["signal"]
    view.plot(np.arange(4), np.arange(4), gid="signal")
    view.scatter(np.arange(3), np.arange(3), gid="points", color=["red", "green", "blue"])
    scatter = view.figure._plot_items["points"]
    view.scatter(np.arange(2), np.arange(2), gid="points", color=["cyan", "magenta"], marker="^")

    assert view.figure._plot_items["signal"] is line
    assert view.figure._plot_items["points"] is scatter
    assert scatter.opts["symbol"] == "t1"
    assert [point.brush().color().name() for point in scatter.points()] == ["#00ffff", "#ff00ff"]


def test_canvas_supports_legend_and_colored_vertical_lines(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphCanvas(parent)
    qtbot.addWidget(view.widget)

    view.figure.set_legend([LegendEntry("selected", "blue"), LegendEntry("user", "black", marker="^")])
    view.add_vlines([1.0, 2.0], gid="isotopes", color=["gray", "black"])

    assert view.figure._legend is not None
    assert len(view.figure._legend.items) == 2
    lines = view.figure._annotation_items["isotopes"]
    assert [line.pen.color().name() for line in lines] == ["#808080", "#000000"]


def test_canvas_emits_ctrl_selection_and_double_click(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphCanvas(parent)
    qtbot.addWidget(view.widget)
    view.widget.resize(400, 300)
    view.widget.show()
    view.plot(np.arange(10), np.arange(10))
    start, end = QPoint(100, 100), QPoint(200, 180)
    selections: list[tuple[float, float, float, float]] = []
    clicks: list[tuple[float, float]] = []
    states: list[bool] = []
    view.figure.evt_ctrl_released.connect(selections.append)
    view.figure.evt_ctrl_double_click.connect(clicks.append)
    view.figure.evt_ctrl_changed.connect(states.append)

    viewport = view.figure.viewport()
    qtbot.mousePress(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=start)
    qtbot.mouseMove(viewport, end)
    qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=end)
    qtbot.mouseDClick(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, pos=end)

    assert states == [True, False]
    assert len(selections) == 1
    assert selections[0][0] < selections[0][1]
    assert selections[0][2] < selections[0][3]
    assert clicks == [pytest.approx(view.figure._map_to_data(end))]


def test_canvas_emits_range_changes_and_updates_theme(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    view = ViewPyQtGraphCanvas(parent)
    qtbot.addWidget(view.widget)
    ranges: list[tuple[float, float, float, float]] = []
    view.figure.evt_range_changed.connect(ranges.append)
    previous_theme = CANVAS.theme

    try:
        view.set_xlim(1.0, 2.0)
        CANVAS.theme = "dark"
        assert ranges
        assert view.figure.backgroundBrush().color().name() == "#000000"
    finally:
        CANVAS.theme = previous_theme
