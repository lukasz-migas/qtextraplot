"""Object outline overlays."""

from __future__ import annotations

import collections.abc as cabc
import typing as ty

import numpy as np
from napari.components.overlays import SceneOverlay
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array

try:
    from pydantic.v1 import validator
except ImportError:
    from pydantic import validator

ColorLike = ty.Any
OutlineData = np.ndarray
OutlineDataLike = OutlineData | ty.Sequence[ty.Sequence[float]]
OutlineInput = OutlineDataLike | ty.Sequence[OutlineDataLike]
WidthLike = float | ty.Sequence[float] | np.ndarray

OUTLINE_DATA_ERROR = "Outline data must be a two-dimensional array with at least two points and two columns."
OUTLINE_SEQUENCE_ERROR = "Outline data must be a two-dimensional array or a sequence of two-dimensional arrays."
OUTLINE_INPUT_ERROR = "Outline data must be an array or a sequence of arrays."
SINGLE_COLOR_ERROR = "A single outline only accepts one color."
COLOR_COUNT_ERROR = "Color count must be one or match the number of outlines."
OUTLINE_WIDTH_ERROR = "Outline width must be positive."
SINGLE_WIDTH_ERROR = "A single outline only accepts one width."
WIDTH_COUNT_ERROR = "Width count must be one or match the number of outlines."
OUTLINE_WIDTHS_ERROR = "Outline widths must be positive."
OBJECT_COLOR_ERROR = "Object outline color must be a single color."
OBJECT_WIDTH_ERROR = "Object outline width must be positive."
MISSING = object()


def _coerce_outline_array(value: ty.Any) -> np.ndarray:
    data = np.asarray(value, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2 or data.shape[1] < 2:
        raise ValueError(OUTLINE_DATA_ERROR)
    return data


def _coerce_outline_arrays(value: OutlineInput | ObjectOutline | ty.Sequence[ObjectOutline]) -> tuple[np.ndarray, ...]:
    if isinstance(value, ObjectOutline):
        return (value.data,)
    if isinstance(value, np.ndarray):
        if value.ndim == 2:
            return (_coerce_outline_array(value),)
        if value.ndim == 3:
            return tuple(_coerce_outline_array(outline) for outline in value)
        raise ValueError(OUTLINE_SEQUENCE_ERROR)

    if isinstance(value, cabc.Sequence):
        if not value:
            return ()
        if all(isinstance(outline, ObjectOutline) for outline in value):
            return tuple(ty.cast(ObjectOutline, outline).data for outline in value)
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError):
            return tuple(_coerce_outline_array(outline) for outline in value)
        if array.ndim == 2:
            return (_coerce_outline_array(array),)
        if array.ndim == 3:
            return tuple(_coerce_outline_array(outline) for outline in array)
        return tuple(_coerce_outline_array(outline) for outline in value)

    raise TypeError(OUTLINE_INPUT_ERROR)


def _coerce_colors(color: ColorLike, n_outlines: int) -> tuple[np.ndarray, ...]:
    colors = transform_color(color)
    if len(colors) == 1:
        return tuple(colors[0].copy() for _ in range(n_outlines))
    if n_outlines == 1:
        raise ValueError(SINGLE_COLOR_ERROR)
    if len(colors) != n_outlines:
        raise ValueError(COLOR_COUNT_ERROR)
    return tuple(np.asarray(color_, dtype=float) for color_ in colors)


def _coerce_widths(width: WidthLike, n_outlines: int) -> tuple[float, ...]:
    widths = np.asarray(width, dtype=float)
    if widths.ndim == 0 or widths.size == 1:
        width_value = float(widths.reshape(-1)[0])
        if width_value <= 0:
            raise ValueError(OUTLINE_WIDTH_ERROR)
        return (width_value,) * n_outlines
    if n_outlines == 1:
        raise ValueError(SINGLE_WIDTH_ERROR)
    if widths.ndim != 1 or widths.size != n_outlines:
        raise ValueError(WIDTH_COUNT_ERROR)
    if np.any(widths <= 0):
        raise ValueError(OUTLINE_WIDTHS_ERROR)
    return tuple(float(width_value) for width_value in widths)


def normalize_object_outlines(
    outlines: OutlineInput | ObjectOutline | ty.Sequence[ObjectOutline],
    color: ColorLike = "red",
    width: WidthLike = 1.0,
) -> tuple[ObjectOutline, ...]:
    """Normalize outline data and style into object outline models."""
    outline_arrays = _coerce_outline_arrays(outlines)
    colors = _coerce_colors(color, len(outline_arrays))
    widths = _coerce_widths(width, len(outline_arrays))
    return tuple(
        ObjectOutline(data=outline, color=color_, width=width_)
        for outline, color_, width_ in zip(outline_arrays, colors, widths, strict=True)
    )


class ObjectOutline(EventedModel):
    """Single object outline."""

    data: np.ndarray
    color: Array[float, (4,)] = (1.0, 0.0, 0.0, 1.0)
    width: float = 1.0

    @validator("data", pre=True, always=True)
    def _coerce_data(cls, value: ty.Any) -> np.ndarray:
        return _coerce_outline_array(value)

    @validator("color", pre=True, always=True)
    def _coerce_color(cls, value: ColorLike) -> np.ndarray:
        colors = transform_color(value)
        if len(colors) != 1:
            raise ValueError(OBJECT_COLOR_ERROR)
        return colors[0]

    @validator("width", pre=True, always=True)
    def _coerce_width(cls, value: float) -> float:
        width = float(value)
        if width <= 0:
            raise ValueError(OBJECT_WIDTH_ERROR)
        return width


class ObjectOutlinesOverlay(SceneOverlay):
    """Object outlines rendered over image data."""

    outlines: tuple[ObjectOutline, ...] = ()
    target_layer: str | None = None
    closed: bool = True

    def __init__(self, **data: ty.Any):
        color = data.pop("color", MISSING)
        width = data.pop("width", MISSING)
        if "outlines" in data and (color is not MISSING or width is not MISSING):
            data["outlines"] = normalize_object_outlines(
                data["outlines"],
                color="red" if color is MISSING else color,
                width=1.0 if width is MISSING else width,
            )
        super().__init__(**data)

    @validator("outlines", pre=True, always=True)
    def _coerce_outlines(cls, value: ty.Any) -> tuple[ObjectOutline, ...]:
        if value is None:
            return ()
        if isinstance(value, ObjectOutline):
            return (value,)
        if isinstance(value, cabc.Sequence) and all(isinstance(outline, ObjectOutline) for outline in value):
            return tuple(value)
        return normalize_object_outlines(value)

    def set_outlines(
        self,
        outlines: OutlineInput | ObjectOutline | ty.Sequence[ObjectOutline],
        color: ColorLike = "red",
        width: WidthLike = 1.0,
    ) -> None:
        """Set outline coordinate data and drawing style."""
        self.outlines = normalize_object_outlines(outlines, color=color, width=width)


__all__ = [
    "ColorLike",
    "ObjectOutline",
    "ObjectOutlinesOverlay",
    "OutlineData",
    "OutlineDataLike",
    "OutlineInput",
    "WidthLike",
    "normalize_object_outlines",
]
