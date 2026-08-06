"""Tests for the napari scale-bar controls."""

import warnings

import numpy as np
from napari.utils._units import get_unit_registry

from qtextraplot._napari.component_controls.qt_scalebar_controls import (
    QtScaleBarControls,
)
from qtextraplot._napari.image.components.viewer_model import Viewer


def test_scalebar_controls_use_layer_units(qtbot) -> None:
    """The controls should use napari 0.8 layer units without warnings."""
    viewer = Viewer()
    layer = viewer.add_image(
        np.zeros((4, 4)),
        scale=(2.5, 2.5),
        units=("um", "um"),
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        controls = QtScaleBarControls(viewer)
    qtbot.addWidget(controls)

    assert controls.units_combobox.currentData() == "um"
    assert controls.pixel_size.value() == 2.5

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        controls.pixel_size.setValue(3.5)
    assert np.all(layer.scale == 3.5)
    assert all(unit == "micrometer" for unit in map(str, layer.units))

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        controls.units_combobox.setCurrentIndex(
            controls.units_combobox.findData("px"),
        )
    assert np.all(layer.scale == 1.0)
    assert all(unit == get_unit_registry().pixel for unit in layer.units)


def test_scalebar_controls_without_layers(qtbot) -> None:
    """The controls should retain safe defaults when no layers exist."""
    controls = QtScaleBarControls(Viewer())
    qtbot.addWidget(controls)

    assert controls.units_combobox.currentData() == ""
    assert controls.pixel_size.value() == 1.0
