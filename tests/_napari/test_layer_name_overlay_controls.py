"""Tests for layer name overlay controls."""

from __future__ import annotations

import numpy as np
import pytest
from qtpy.QtWidgets import QWidget

napari = pytest.importorskip("napari", reason="napari is not installed")
try:
    from napari.components.overlays.text import LayerNameOverlay
except ImportError:
    pytest.skip("LayerNameOverlay requires napari 0.8 or newer", allow_module_level=True)

from qtextraplot._napari._constants import CanvasPosition  # noqa: E402
from qtextraplot._napari.component_controls.qt_layer_name_overlay_controls import (  # noqa: E402
    QtLayerNameOverlayControls,
)
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar  # noqa: E402


class _Event:
    """Small event stand-in for the layer collection in control tests."""

    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def disconnect(self, callback) -> None:
        self._callbacks.remove(callback)

    def emit(self) -> None:
        for callback in tuple(self._callbacks):
            callback()


class _LayerList(list):
    """List-like layer collection with the events used by the controls."""

    def __init__(self, layers=()) -> None:
        super().__init__(layers)
        self.events = type(
            "LayerEvents",
            (),
            {name: _Event() for name in ("inserted", "removed", "changed")},
        )()

    def append(self, layer) -> None:
        super().append(layer)
        self.events.inserted.emit()

    def remove(self, layer) -> None:
        super().remove(layer)
        self.events.removed.emit()


class _Viewer:
    """Minimal viewer model required by the layer-name controls."""

    def __init__(self, layers=()) -> None:
        self.layers = _LayerList(layers)


def _layer(name: str):
    """Create a fake layer with a napari layer name overlay."""
    return type("Layer", (), {"name": name, "name_overlay": LayerNameOverlay()})()


def _viewer_with_name_layers() -> tuple[_Viewer, list]:
    """Return a viewer with two layers supporting name overlays."""
    layers = [_layer("First"), _layer("Second")]
    viewer = _Viewer(layers)
    return viewer, layers


def test_layer_name_overlay_controls_are_safe_without_layers(qtbot) -> None:
    """The popup should initialize safely before any layers are added."""
    controls = QtLayerNameOverlayControls(_Viewer())
    qtbot.addWidget(controls)

    assert not controls.visible_checkbox.isEnabled()
    assert controls.font_size_spinbox.value() == 10
    assert controls.opacity_spinbox.value() == 1


def test_layer_name_overlay_controls_update_all_layers(qtbot) -> None:
    """Widget changes should be applied to every layer name overlay."""
    viewer, layers = _viewer_with_name_layers()
    controls = QtLayerNameOverlayControls(viewer)
    qtbot.addWidget(controls)

    controls.visible_checkbox.setChecked(True)
    controls.color_swatch.setColor("red")
    controls.position_combobox.setCurrentIndex(controls.position_combobox.findData(CanvasPosition.BOTTOM_LEFT))
    controls.font_size_spinbox.setValue(18)
    controls.opacity_spinbox.setValue(0.35)

    for layer in layers:
        assert layer.name_overlay.visible
        np.testing.assert_allclose(layer.name_overlay.color, [1, 0, 0, 1])
        assert layer.name_overlay.position == CanvasPosition.BOTTOM_LEFT
        assert layer.name_overlay.font_size == 18
        assert layer.name_overlay.opacity == 0.35


def test_layer_name_overlay_controls_sync_external_changes(qtbot) -> None:
    """External model changes should update the popup widgets."""
    viewer, layers = _viewer_with_name_layers()
    controls = QtLayerNameOverlayControls(viewer)
    qtbot.addWidget(controls)

    layers[0].name_overlay.font_size = 22
    layers[0].name_overlay.opacity = 0.25
    layers[0].name_overlay.position = CanvasPosition.TOP_RIGHT
    layers[0].name_overlay.color = [0, 1, 0, 1]

    assert controls.font_size_spinbox.value() == 22
    assert controls.opacity_spinbox.value() == 0.25
    assert controls.position_combobox.currentData() == CanvasPosition.TOP_RIGHT
    np.testing.assert_allclose(controls.color_swatch.color, [0, 1, 0, 1])


def test_layer_name_overlay_controls_use_first_mixed_value(qtbot) -> None:
    """Mixed values should be represented by the first layer deterministically."""
    viewer, layers = _viewer_with_name_layers()
    layers[0].name_overlay.font_size = 12
    layers[1].name_overlay.font_size = 24

    controls = QtLayerNameOverlayControls(viewer)
    qtbot.addWidget(controls)

    assert controls.font_size_spinbox.value() == 12


def test_layer_name_overlay_controls_refresh_when_layers_change(qtbot) -> None:
    """Adding and removing layers should refresh the available controls."""
    viewer = _Viewer()
    controls = QtLayerNameOverlayControls(viewer)
    qtbot.addWidget(controls)

    layer = _layer("First")
    viewer.layers.append(layer)
    assert controls.visible_checkbox.isEnabled()

    viewer.layers.remove(layer)
    assert not controls.visible_checkbox.isEnabled()


def test_toolbar_layer_name_button_toggles_visibility(qtbot) -> None:
    """The toolbar button should toggle and synchronize layer name visibility."""
    viewer, layers = _viewer_with_name_layers()
    for layer in layers:
        layer.name_overlay.visible = True

    qt_viewer = QWidget()
    qt_viewer.viewer = viewer
    qt_viewer.on_toggle_controls_dialog = lambda: None
    qtbot.addWidget(qt_viewer)
    viewer.grid = type("Grid", (), {"enabled": False})()
    viewer.text_overlay = type("TextOverlay", (), {"visible": False})()
    viewer.scale_bar = type("ScaleBar", (), {"visible": False})()
    viewer.reset_view = lambda: None
    viewer.clear_canvas = lambda: None
    toolbar = QtViewToolbar(
        view=None,
        viewer=viewer,
        qt_viewer=qt_viewer,
        allow_crosshair=False,
        allow_object_outlines=False,
        allow_legend=False,
    )
    qtbot.addWidget(toolbar)

    assert toolbar.tools_name_overlay_btn.isChecked()
    assert toolbar.tools_name_overlay_btn.menu_enabled

    toolbar._toggle_layer_names_visible(False)

    assert all(not layer.name_overlay.visible for layer in layers)
    assert not toolbar.tools_name_overlay_btn.isChecked()
