"""Base layer controls."""

import qtextra.helpers as hp
from napari._qt.layer_controls.qt_layer_controls_base import QtLayerControls as _QtLayerControls
from napari.layers import Layer
from napari.utils.events import Event


class QtLayerControls(_QtLayerControls):
    """Override QtLayerControls.."""

    def __init__(self, layer: Layer):
        super().__init__(layer)
        editable_checkbox = hp.make_checkbox(self, "")
        editable_checkbox.stateChanged.connect(self.changeEditable)
        self.editable_checkbox = editable_checkbox
        self.opacityLabel.setText("Opacity")

    def changeEditable(self, state):
        """Change editability value on the layer model."""
        with self.layer.events.blocker(self._on_editable_or_visible_change):
            self.layer.editable = state

    def _on_editable_or_visible_change(self, _event: Event = None) -> None:
        """Receive layer model opacity change event and update opacity slider."""
        with self.layer.events.editable.blocker():
            self.editable_checkbox.setChecked(self.layer.editable)
