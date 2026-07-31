"""Public exports for napari-backed image views."""

from qtextraplot._napari._utilities import set_layer_spatial_calibration
from qtextraplot._napari.image import NapariImageView

__all__ = ["NapariImageView", "set_layer_spatial_calibration"]
