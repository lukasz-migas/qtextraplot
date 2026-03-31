"""Tests for pyqtgraph-backed views."""

from __future__ import annotations

import numpy as np
import pytest
from qtpy.QtWidgets import QWidget

pg = pytest.importorskip("pyqtgraph")

from qtextraplot._pyqtgraph import ViewPyQtGraphCanvas, ViewPyQtGraphImage, ViewPyQtGraphLine, ViewPyQtGraphScatter


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
