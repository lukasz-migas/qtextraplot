"""Canvas legend overlay models."""

from __future__ import annotations

import collections.abc as cabc
import typing as ty

import numpy as np
from napari.components.overlays import CanvasOverlay
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array

from qtextraplot._napari._constants import SYMBOL_ALIAS, CanvasPosition

try:
    from pydantic.v1 import validator
except ImportError:
    from pydantic import validator

if ty.TYPE_CHECKING:
    from napari.layers import Points

ColorLike = ty.Any

EMPTY_LABEL_ERROR = "Legend entry labels must not be empty."
LEGEND_ENTRY_ERROR = "Legend entries must be LegendEntry instances or mappings."
LEGEND_ENTRIES_ERROR = "Legend entries must be one entry or a sequence of entries."
LEGEND_COLOR_ERROR = "Legend colors must resolve to a single color."
LEGEND_SIZE_ERROR = "Legend sizes and spacing must be positive."
LEGEND_PADDING_ERROR = "Legend padding must be non-negative."
LEGEND_BORDER_ERROR = "Legend border width must be non-negative."
LABEL_PROPERTY_ERROR = "Points legend label property must exist on the layer."


def _coerce_single_color(value: ColorLike) -> np.ndarray:
    colors = transform_color(value)
    if len(colors) != 1:
        raise ValueError(LEGEND_COLOR_ERROR)
    return np.asarray(colors[0], dtype=float)


def _coerce_marker(value: ty.Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        value = value.value
    marker = str(value)
    if not marker or marker.lower() in {"none", "null"}:
        return None
    return str(SYMBOL_ALIAS.get(marker, marker))


def _coerce_entry(value: ty.Any) -> LegendEntry:
    if isinstance(value, LegendEntry):
        return value
    if isinstance(value, cabc.Mapping):
        return LegendEntry(**value)
    raise TypeError(LEGEND_ENTRY_ERROR)


def normalize_legend_entries(entries: LegendInput | LegendEntry | None) -> tuple[LegendEntry, ...]:
    """Normalize legend entry input into legend entry models."""
    if entries is None:
        return ()
    if isinstance(entries, (LegendEntry, cabc.Mapping)):
        return (_coerce_entry(entries),)
    if isinstance(entries, cabc.Sequence) and not isinstance(entries, str):
        return tuple(_coerce_entry(entry) for entry in entries)
    raise TypeError(LEGEND_ENTRIES_ERROR)


def _feature_values(layer: Points, name: str) -> ty.Any:
    if name in layer.properties:
        return np.asarray(layer.properties[name])
    features = getattr(layer, "features", None)
    if features is not None and name in features:
        return np.asarray(features[name])
    raise KeyError(name)


def _optional_feature_values(layer: Points, name: str | None) -> ty.Any:
    if name is None or name.lower() == "none":
        return None
    if name == "symbol":
        return np.asarray(layer.symbol)
    if name == "face":
        return np.asarray(layer.face_color)
    if name == "border":
        return np.asarray(layer.border_color)
    try:
        return _feature_values(layer, name)
    except KeyError:
        return None


def _value_at(values: ty.Any, index: int) -> ty.Any:
    if values is None:
        return None
    try:
        if np.ndim(values) == 0:
            return values
        return values[index]
    except (IndexError, TypeError):
        return values


def _legend_group_key(label: str, marker: ty.Any, color: ty.Any, group_by_style: bool) -> tuple[ty.Any, ...]:
    if not group_by_style:
        return (label,)
    marker_key = _coerce_marker(marker)
    color_key = None
    if color is not None:
        color_key = tuple(np.round(_coerce_single_color(color), 6))
    return (label, marker_key, color_key)


def legend_entries_from_points(
    layer: Points,
    *,
    label_property: str = "label",
    color_source: str = "face",
    marker_source: str = "symbol",
    group_by_style: bool = True,
) -> tuple[LegendEntry, ...]:
    """Create legend entries from a Points layer.

    Duplicate entries are collapsed while preserving distinct marker or color
    styles when requested.
    """
    try:
        labels = _feature_values(layer, label_property)
    except KeyError as error:
        raise ValueError(LABEL_PROPERTY_ERROR) from error

    colors = _optional_feature_values(layer, color_source)
    markers = _optional_feature_values(layer, marker_source)
    entries: list[LegendEntry] = []
    seen: set[tuple[ty.Any, ...]] = set()

    for index, label in enumerate(labels):
        label_text = str(label)
        marker = _value_at(markers, index)
        color = _value_at(colors, index)
        key = _legend_group_key(label_text, marker, color, group_by_style=group_by_style)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            LegendEntry(
                label=label_text,
                marker=marker,
                color=color,
            ),
        )
    return tuple(entries)


class LegendEntry(EventedModel):
    """Single legend row."""

    label: str
    marker: str | None = None
    color: Array[float, (4,)] | None = None
    colormap: str | None = None

    @validator("label", pre=True, always=True)
    def _coerce_label(cls, value: ty.Any) -> str:
        label = str(value)
        if not label:
            raise ValueError(EMPTY_LABEL_ERROR)
        return label

    @validator("marker", pre=True, always=True)
    def _validate_marker(cls, value: ty.Any) -> str | None:
        return _coerce_marker(value)

    @validator("color", pre=True, always=True)
    def _validate_color(cls, value: ColorLike | None) -> np.ndarray | None:
        if value is None:
            return None
        return _coerce_single_color(value)

    @validator("colormap", pre=True, always=True)
    def _validate_colormap(cls, value: ty.Any) -> str | None:
        if value is None:
            return None
        colormap = str(value)
        if not colormap:
            return None
        return colormap


LegendEntryLike = LegendEntry | ty.Mapping[str, ty.Any]
LegendInput = LegendEntryLike | ty.Sequence[LegendEntryLike]


class LegendOverlay(CanvasOverlay):
    """Canvas-space legend rendered above image layers."""

    position: CanvasPosition | ty.Any = CanvasPosition.TOP_RIGHT
    entries: tuple[LegendEntry, ...] = ()
    text_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    font_size: float = 10.0
    marker_size: float = 10.0
    row_spacing: float = 4.0
    padding: float = 6.0
    background_color: Array[float, (4,)] = (0.0, 0.0, 0.0, 0.65)
    border_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 0.8)
    border_width: float = 1.0
    source_layer: str | None = None
    label_property: str = "label"
    color_source: str = "face"
    marker_source: str = "symbol"
    group_by_style: bool = True
    sync_with_source: bool = False

    @validator("entries", pre=True, always=True)
    def _coerce_entries(cls, value: ty.Any) -> tuple[LegendEntry, ...]:
        return normalize_legend_entries(value)

    @validator("text_color", "background_color", "border_color", pre=True, always=True)
    def _coerce_color(cls, value: ColorLike) -> np.ndarray:
        return _coerce_single_color(value)

    @validator("font_size", "marker_size", "row_spacing", pre=True, always=True)
    def _coerce_positive_number(cls, value: float) -> float:
        number = float(value)
        if number <= 0:
            raise ValueError(LEGEND_SIZE_ERROR)
        return number

    @validator("padding", pre=True, always=True)
    def _coerce_padding(cls, value: float) -> float:
        padding = float(value)
        if padding < 0:
            raise ValueError(LEGEND_PADDING_ERROR)
        return padding

    @validator("border_width", pre=True, always=True)
    def _coerce_border_width(cls, value: float) -> float:
        width = float(value)
        if width < 0:
            raise ValueError(LEGEND_BORDER_ERROR)
        return width

    def set_entries(self, entries: LegendInput | LegendEntry | None) -> None:
        """Set legend row entries."""
        self.entries = normalize_legend_entries(entries)


__all__ = [
    "ColorLike",
    "LegendEntry",
    "LegendEntryLike",
    "LegendInput",
    "LegendOverlay",
    "legend_entries_from_points",
    "normalize_legend_entries",
]
