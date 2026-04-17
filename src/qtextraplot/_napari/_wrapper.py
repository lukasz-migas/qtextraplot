"""Viewer base."""

from __future__ import annotations

import typing as ty
from abc import ABC
from contextlib import suppress

from napari.components.layerlist import LayerList
from napari.layers import Image, Layer


class ViewerBase(ABC):
    """Base class for viewer implementations."""

    IS_VISPY = True
    PLOT_ID = ""
    viewer: ty.Any
    widget: ty.Any
    _callbacks = None

    @property
    def is_vispy(self) -> bool:
        """Flag to say whether this is a vispy-based visualisation."""
        return self.IS_VISPY

    @property
    def figure(self):
        """Canvas."""
        return self.widget.canvas

    @property
    def camera(self):
        """Get camera."""
        return self.widget.view.camera

    @property
    def vispy_camera(self):
        """Get camera."""
        return self.widget.canvas.camera._view.camera

    def _clear(self, _evt=None) -> None:  # noqa: B027
        """Clear canvas."""

    def _reset_text_overlay(self) -> None:
        """Clear overlay text if the viewer exposes a text overlay."""
        with suppress(AttributeError):
            self.viewer.text_overlay.text = ""

    def _clear_tracked_layers(self, *attr_names: str) -> None:
        """Reset tracked wrapper layer references to ``None``."""
        for attr_name in attr_names:
            setattr(self, attr_name, None)

    def _clear_tracked_layer_on_remove(self, removed_layer: Layer, *attr_names: str) -> None:
        """Reset tracked layer references when the corresponding layer is removed."""
        for attr_name in attr_names:
            layer = getattr(self, attr_name, None)
            if layer is not None and layer.name == removed_layer.name:
                setattr(self, attr_name, None)

    def clear(self) -> None:
        """Clear canvas."""
        self._clear()
        self.viewer.layers.clear()
        self._reset_text_overlay()

    def clear_and_exclude(self, *name_or_layer: ty.Iterable[str | Layer]) -> None:
        """Clear canvas but exclude some layers."""
        exclude_names = set()
        for item in name_or_layer:
            if isinstance(item, str):
                exclude_names.add(item)
            elif isinstance(item, Layer) and item.name:
                exclude_names.add(item.name)
        for layer in list(self.viewer.layers):
            if layer.name not in exclude_names:
                self.viewer.layers.remove(layer)
        self._reset_text_overlay()

    def close(self) -> None:
        """Close the view instance."""
        self.viewer.layers.clear()
        self.widget.close()

    @property
    def layers(self) -> LayerList:
        """Get layer list."""
        return self.viewer.layers

    def get_layer(self, name: str) -> Layer | None:
        """Get layer."""
        try:
            return self.viewer.layers[name]
        except KeyError:
            return None

    def remove_layer(self, name: str | Layer, silent: bool = True) -> bool:
        """Remove layer with `name`."""
        if hasattr(name, "name"):
            name = name.name  # it's actually a layer
        try:
            self.viewer.layers.remove(name)
            return True  # noqa: TRY300
        except (ValueError, KeyError) as err:
            if not silent:
                print(f"Failed to remove layer `{name}`\n{err}")
        return False

    def remove_layers(self, names: ty.Iterable[str]) -> None:
        """Remove multiple layers."""
        for name in names:
            self.remove_layer(name)

    def try_reuse(self, name: str, cls: ty.Type[Layer], reuse: bool = True) -> Layer | None:
        """Try retrieving layer from the layer list."""
        if not reuse:
            self.remove_layer(name, silent=True)
            return None
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, cls) else None
        except KeyError:
            return None

    def select_one_layer(self, layer: Layer) -> None:
        """Clear current selection and only select one layer."""
        self.viewer.layers.selection.clear()
        self.viewer.layers.selection.add(layer)

    def deselect_one_layer(self, layer: Layer) -> None:
        """Deselect layer."""
        with suppress(KeyError):
            self.viewer.layers.selection.remove(layer)

    def get_layers_of_type(self, cls: Layer) -> ty.List[Layer]:
        """Get all layers of type."""
        layers = []
        for layer in self.viewer.layers:
            if isinstance(layer, cls):
                layers.append(layer)
        return layers

    def get_layers_of_type_with_attr_value(self, cls: Layer, attr: str, value: ty.Any) -> ty.List[Layer]:
        """Get all layers of type."""
        layers = []
        for layer in self.viewer.layers:
            if isinstance(layer, cls) and getattr(layer, attr) == value:
                layers.append(layer)
        return layers

    def update_attribute(self, name: str, **kwargs: ty.Any) -> None:
        """Update attribute."""
        layer = self.get_layer(name)
        if layer:
            for attr, value in kwargs.items():
                if hasattr(layer, attr):
                    with suppress(Exception):
                        setattr(layer, attr, value)

    @staticmethod
    def update_image_contrast_limits(image_layer: Image, new_range: ty.Tuple | None = None):
        """Update contrast limits for specified layer."""
        if new_range is None or len(new_range) != 2:
            new_range = image_layer._calc_data_range()
        image_layer.contrast_limits_range = new_range
        image_layer._contrast_limits = tuple(image_layer.contrast_limits_range)
        image_layer.contrast_limits = image_layer._contrast_limits
        image_layer._update_dims()

    def update_image(self, image_layer: Image, new_data) -> None:
        """Update image data for specified layer."""
        image_layer.data = new_data
        self.update_image_contrast_limits(image_layer)
