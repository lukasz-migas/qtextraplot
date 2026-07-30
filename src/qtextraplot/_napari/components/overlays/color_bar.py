"""Colorbar."""

from __future__ import annotations

import numpy as np
from napari.components.overlays import CanvasOverlay
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events.custom_types import Array
from pydantic import ConfigDict, field_validator

ColorBarItem = tuple[np.ndarray, str, tuple[float, float]]


class ColorBarOverlay(CanvasOverlay):
    """Colorbar object."""

    model_config = CanvasOverlay.model_config | ConfigDict(arbitrary_types_allowed=True)

    # fields
    border_width: int = 1
    border_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_size: int = 7
    colormap: str = "viridis"
    data: tuple[ColorBarItem, ...] | None = None

    @field_validator("border_color", "label_color", mode="before")
    @classmethod
    def _coerce_color(cls, v):
        return transform_color(v)[0]
