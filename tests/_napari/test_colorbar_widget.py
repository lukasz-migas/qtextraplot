"""Tests for the napari image colorbar widget."""

from __future__ import annotations

import numpy as np
from napari.components import ViewerModel

from qtextraplot._napari.widgets import QtNapariImageColorbarWidget


def _image_data() -> np.ndarray:
    return np.linspace(0.0, 1.0, 16).reshape(4, 4)


def test_napari_colorbar_includes_only_scalar_image_layers(qtbot) -> None:
    viewer = ViewerModel()
    image = viewer.add_image(_image_data(), name="Image", colormap="magenta")
    viewer.add_image(np.zeros((4, 4, 3)), name="RGB", rgb=True)
    viewer.add_points(np.zeros((1, 2)), name="Points")

    widget = QtNapariImageColorbarWidget(viewer)
    qtbot.addWidget(widget)

    assert len(widget.stack.widgets) == 1
    assert widget.widget_for_layer(image) is widget.stack.widgets[0]


def test_napari_colorbar_tracks_added_and_removed_image_layers(qtbot) -> None:
    viewer = ViewerModel()
    widget = QtNapariImageColorbarWidget(viewer)
    qtbot.addWidget(widget)
    widget.resize(760, widget.sizeHint().height())
    assert widget.stack.widgets == ()

    image = viewer.add_image(_image_data(), name="Image", colormap="green")
    assert len(widget.stack.widgets) == 1
    second = viewer.add_image(_image_data(), name="Second", colormap="blue")
    height_with_two_rows = widget.height()
    assert len(widget.stack.widgets) == 2

    row = widget.widget_for_layer(image)
    assert row is not None
    viewer.layers.remove(second)
    assert len(widget.stack.widgets) == 1
    assert widget.width() == 760
    assert widget.height() < height_with_two_rows
    assert widget.widget_for_layer(second) is None

    viewer.layers.remove(image)
    assert widget.stack.widgets == ()

    image.contrast_limits = (0.0, 1.0)
    row.set_limits((0.2, 0.4))
    assert tuple(image.contrast_limits) == (0.0, 1.0)


def test_napari_colorbar_updates_from_layer_colormap(qtbot) -> None:
    viewer = ViewerModel()
    image = viewer.add_image(_image_data(), name="Image", colormap="magenta")
    widget = QtNapariImageColorbarWidget(viewer)
    qtbot.addWidget(widget)
    row = widget.widget_for_layer(image)
    assert row is not None

    image.colormap = "green"

    assert row._slider._color_stops[-1][1].green() > 200
    assert row._slider._color_stops[-1][1].red() < 80


def test_napari_colorbar_updates_from_layer_contrast(qtbot) -> None:
    viewer = ViewerModel()
    image = viewer.add_image(_image_data(), name="Image", colormap="blue")
    widget = QtNapariImageColorbarWidget(viewer)
    qtbot.addWidget(widget)
    row = widget.widget_for_layer(image)
    assert row is not None

    image.contrast_limits_range = (0.0, 2.0)
    image.contrast_limits = (0.4, 1.0)

    assert row.value() == (0.4, 1.0)
    assert row._overflow_label.text() == "200%"
    assert image.colormap.low_color is not None
    assert float(image.colormap.low_color[-1]) == 0.0


def test_napari_colorbar_updates_layer_from_widget(qtbot) -> None:
    viewer = ViewerModel()
    image = viewer.add_image(_image_data(), name="Image", colormap="yellow")
    widget = QtNapariImageColorbarWidget(viewer)
    qtbot.addWidget(widget)
    row = widget.widget_for_layer(image)
    assert row is not None

    row.set_limits((0.25, 0.75))
    assert tuple(image.contrast_limits) == (0.25, 0.75)
    assert image.colormap.low_color is not None
    assert float(image.colormap.low_color[-1]) == 0.0

    row.set_limits((0.0, 0.75))
    assert tuple(image.contrast_limits) == (0.0, 0.75)
    assert image.colormap.low_color is None
