"""Layer-bound controls for embedded napari viewers."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from napari._qt.layer_controls.qt_labels_controls import QtLabelsControls as _QtLabelsControls
from napari._qt.layer_controls.qt_points_controls import QtPointsControls as _QtPointsControls
from napari._qt.layer_controls.qt_shapes_controls import QtShapesControls as _QtShapesControls
from napari.layers import Labels, Points, Shapes


def _disconnect_global_mode_actions(controls: ty.Any) -> None:
    """Keep mode buttons bound only to the layer stored by each button."""
    for button in controls._MODE_BUTTONS.values():
        with suppress(TypeError):
            button.clicked.disconnect()


class QtLayerBoundLabelsControls(_QtLabelsControls):
    """Napari labels controls that always modify their assigned layer."""

    def __init__(self, layer: Labels) -> None:
        super().__init__(layer)
        _disconnect_global_mode_actions(self)


class QtLayerBoundPointsControls(_QtPointsControls):
    """Napari points controls that always modify their assigned layer."""

    def __init__(self, layer: Points) -> None:
        super().__init__(layer)
        _disconnect_global_mode_actions(self)


class QtLayerBoundShapesControls(_QtShapesControls):
    """Napari shapes controls that always modify their assigned layer."""

    def __init__(self, layer: Shapes) -> None:
        super().__init__(layer)
        _disconnect_global_mode_actions(self)
