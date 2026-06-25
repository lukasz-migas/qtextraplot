"""Regression tests for napari mode compatibility."""

from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import napari.layers.shapes._shapes_key_bindings as shapes_key_bindings
import numpy as np
from napari.layers import Labels, Points, Shapes
from napari.layers.shapes._shapes_constants import Mode
from napari.utils.action_manager import action_manager

from qtextraplot._napari._compat import install_mode_enum_compatibility
from qtextraplot._napari.image.extract import ImageLabelsROIExtractPopup, ImageShapesROIExtractPopup
from qtextraplot._napari.layer_controls.qt_layer_bound_controls import (
    QtLayerBoundLabelsControls,
    QtLayerBoundPointsControls,
    QtLayerBoundShapesControls,
)
from qtextraplot._napari.widgets.qt_mode_button import QtModeRadioButton


class _StaleShapesMode(str, Enum):
    ADD_RECTANGLE = "stale_rectangle"
    ADD_POLYGON_LASSO = "stale_polygon_lasso"


def test_layer_accepts_equivalent_mode_from_stale_enum() -> None:
    layer = Shapes(ndim=2)

    layer.mode = _StaleShapesMode.ADD_RECTANGLE

    assert layer.mode == "add_rectangle"


def test_native_shapes_action_accepts_stale_mode_enum(monkeypatch) -> None:
    layer = Shapes(ndim=2)
    monkeypatch.setattr(shapes_key_bindings, "Mode", _StaleShapesMode)

    shapes_key_bindings.activate_add_rectangle_mode(layer)

    assert layer.mode == "add_rectangle"


def test_native_lasso_action_resolves_stale_enum_by_member_name(monkeypatch) -> None:
    layer = Shapes(ndim=2)
    monkeypatch.setattr(shapes_key_bindings, "Mode", _StaleShapesMode)

    shapes_key_bindings.activate_add_polygon_lasso_mode(layer)

    assert layer.mode == "add_polygon_lasso"


def test_mode_compatibility_install_is_idempotent() -> None:
    installed_helper = Shapes._mode_setter_helper

    install_mode_enum_compatibility()

    assert Shapes._mode_setter_helper is installed_helper


def test_layer_still_accepts_current_enum_and_string() -> None:
    layer = Shapes(ndim=2)

    layer.mode = Mode.ADD_POLYGON
    assert layer.mode == "add_polygon"

    layer.mode = "add_ellipse"
    assert layer.mode == "add_ellipse"


def test_mode_button_stores_and_assigns_string(qtbot) -> None:
    layer = Shapes(ndim=2)
    button = QtModeRadioButton(layer, "rectangle", Mode.ADD_RECTANGLE)
    qtbot.addWidget(button)

    assert button.mode == "add_rectangle"

    button.setChecked(True)

    assert layer.mode == "add_rectangle"


def test_extract_popup_controls_change_the_supplied_layer(qtbot, monkeypatch) -> None:
    layer = Shapes(ndim=2)

    controls = ImageShapesROIExtractPopup._make_layer_controls(SimpleNamespace(layer=layer))
    qtbot.addWidget(controls)

    assert isinstance(controls, QtLayerBoundShapesControls)
    monkeypatch.setattr(
        action_manager,
        "trigger",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("global action triggered")),
    )

    controls.polygon_lasso_button.click()

    assert layer.mode == "add_polygon_lasso"


def test_labels_popup_controls_change_the_supplied_layer(qtbot, monkeypatch) -> None:
    layer = Labels(np.zeros((2, 2), dtype=np.uint8))

    controls = ImageLabelsROIExtractPopup._make_layer_controls(SimpleNamespace(layer=layer))
    qtbot.addWidget(controls)

    assert isinstance(controls, QtLayerBoundLabelsControls)
    monkeypatch.setattr(
        action_manager,
        "trigger",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("global action triggered")),
    )

    controls.erase_button.click()

    assert layer.mode == "erase"


def test_points_controls_change_the_supplied_layer(qtbot, monkeypatch) -> None:
    layer = Points(ndim=2)
    controls = QtLayerBoundPointsControls(layer)
    qtbot.addWidget(controls)

    monkeypatch.setattr(
        action_manager,
        "trigger",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("global action triggered")),
    )

    controls.addition_button.click()

    assert layer.mode == "add"
