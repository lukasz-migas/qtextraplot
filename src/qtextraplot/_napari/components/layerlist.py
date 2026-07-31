from collections.abc import Iterable

from napari.components.layerlist import LayerList as _LayerList
from napari.layers import Layer
from napari.layers.utils.layer_utils import LayerListExtent


class LayerList(_LayerList):
    """Monkey-patched layer list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def selection_extent(self) -> LayerListExtent:
        """Extent of layers in data and world coordinates."""
        return self.get_extent(self.selection)

    def extent_for(self, layers: Iterable[Layer]) -> LayerListExtent:
        """Extent of layers in data and world coordinates."""
        return self.get_extent(layers)

    def toggle_selected_editable(self) -> None:
        """Toggle editable of selected layers."""
        for layer in self:
            if layer in self.selection:
                layer.editable = not layer.editable

    def remove_all(self) -> None:
        """Remove all layers."""
        self.select_all()
        self.remove_selected()
