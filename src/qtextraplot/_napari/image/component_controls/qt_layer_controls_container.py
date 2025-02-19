"""Overrides for controls."""

from qtextraplot._napari.common.layer_controls.qt_layer_controls_container import (
    QtLayerControlsContainer as _QtLayerControlsContainer,
)


class QtLayerControlsContainer(_QtLayerControlsContainer):
    """Layer controls."""

    def enterEvent(self, event):
        """Emit our own event when mouse enters the canvas."""
        from qtextraplot._napari.image.qt_viewer import QtViewer

        QtViewer.set_current_index(self.qt_viewer.current_index)
        super().enterEvent(event)
