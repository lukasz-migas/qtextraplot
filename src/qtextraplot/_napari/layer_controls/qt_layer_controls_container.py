"""Layer controls container compatible with napari 0.8."""

from __future__ import annotations

from typing import Any

from napari._qt.layer_controls import qt_layer_controls_container as napari_layer_controls
from napari._qt.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer as NapariQtLayerControlsContainer,
)
from napari.layers import Labels, Points, Shapes
from napari.utils.events import Event

from qtextraplot._napari.layer_controls.qt_layer_bound_controls import (
    QtLayerBoundLabelsControls,
    QtLayerBoundPointsControls,
    QtLayerBoundShapesControls,
)

try:
    from napari_plot._qt.layer_controls.qt_centroids_controls import QtCentroidControls
    from napari_plot._qt.layer_controls.qt_infline_controls import QtInfLineControls
    from napari_plot._qt.layer_controls.qt_line_controls import QtLineControls
    from napari_plot._qt.layer_controls.qt_multiline_controls import QtMultiLineControls
    from napari_plot._qt.layer_controls.qt_region_controls import QtRegionControls
    from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
    from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Region, Scatter
except (ImportError, TypeError):
    QtCentroidControls = None
    QtInfLineControls = None
    QtLineControls = None
    QtMultiLineControls = None
    QtRegionControls = None
    QtScatterControls = None
    Centroids = None
    InfLine = None
    Line = None
    MultiLine = None
    Region = None
    Scatter = None


layer_to_controls: dict[type, type] = {
    Labels: QtLayerBoundLabelsControls,
    Points: QtLayerBoundPointsControls,
    Shapes: QtLayerBoundShapesControls,
}

if Centroids is not None:
    layer_to_controls.update(
        {
            Line: QtLineControls,
            Centroids: QtCentroidControls,
            Scatter: QtScatterControls,
            Region: QtRegionControls,
            InfLine: QtInfLineControls,
            MultiLine: QtMultiLineControls,
        },
    )

napari_layer_controls.layer_to_controls.update(layer_to_controls)
create_qt_layer_controls = napari_layer_controls.create_qt_layer_controls


class QtLayerControlsContainer(NapariQtLayerControlsContainer):
    """Display napari and qtextraplot controls for the active layer."""

    def __init__(self, qt_viewer: Any, viewer: Any) -> None:
        self.qt_viewer = qt_viewer
        super().__init__(viewer)
        self.setProperty("emphasized", True)

    def _add(self, event: Event) -> None:
        """Add controls and mark napari's built-ins for scoped styling."""
        super()._add(event)
        controls = self.widgets[event.value]
        controls.setProperty(
            "napari_builtin",
            controls.__class__.__module__.startswith("napari."),
        )


__all__ = ["QtLayerControlsContainer", "create_qt_layer_controls", "layer_to_controls"]
