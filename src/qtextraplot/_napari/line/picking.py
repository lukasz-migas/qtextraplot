"""Hover and click lookups of scatter points in a napari-plot line view."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari_plot.layers import Scatter
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QToolTip

if ty.TYPE_CHECKING:
    from qtextraplot._napari.line.wrapper import NapariLineView

HoverCallback = ty.Callable[[Scatter, int], "str | None"]
PointCallback = ty.Callable[[Scatter, int], None]


def _to_axis(values: ty.Any, scale: str) -> np.ndarray:
    """Map values to displayed axis coordinates: log10 on a log axis (non-positive values become NaN)."""
    values = np.asarray(values, dtype=float)
    if scale != "log":
        return values
    positive = values > 0
    return np.where(positive, np.log10(np.where(positive, values, 1.0)), np.nan)


def _screen_xy(view: NapariLineView, x: ty.Any, y: ty.Any) -> tuple[np.ndarray, np.ndarray]:
    """Convert data coordinates to screen pixels relative to the visible plot area."""
    axis = view.viewer.axis
    xmin, xmax, ymin, ymax = view.viewer.camera.rect
    height, width = view.widget.canvas.size  # napari-plot's canvas reports (height, width)
    tiny = np.finfo(float).tiny
    x_low, x_high = _to_axis([xmin, xmax], axis.x_scale)
    y_low, y_high = _to_axis([ymin, ymax], axis.y_scale)
    sx = (_to_axis(x, axis.x_scale) - x_low) * width / max(float(x_high - x_low), tiny)
    sy = (_to_axis(y, axis.y_scale) - y_low) * height / max(float(y_high - y_low), tiny)
    return sx, sy


def nearest_point(
    view: NapariLineView,
    layers: ty.Sequence[Scatter],
    x: float,
    y: float,
    max_px: float = 8.0,
) -> tuple[Scatter, int] | None:
    """Return the visible scatter layer and index of the point closest to (`x`, `y`) on screen, within `max_px`."""
    best: tuple[float, Scatter, int] | None = None
    cursor_x, cursor_y = _screen_xy(view, np.array([x]), np.array([y]))
    for layer in layers:
        if not layer.visible or not len(layer.data):
            continue
        data = np.asarray(layer.data, dtype=float)
        point_x, point_y = _screen_xy(view, data[:, -1], data[:, -2])  # napari stores points as (y, x)
        distance = np.hypot(point_x - cursor_x, point_y - cursor_y)
        distance[~np.isfinite(distance)] = np.inf
        index = int(np.argmin(distance))
        if distance[index] <= max_px and (best is None or distance[index] < best[0]):
            best = (float(distance[index]), layer, index)
    return None if best is None else (best[1], best[2])


class PointPicker:
    """Calls back with the scatter point under the cursor on hover, click and double-click.

    Created by `NapariLineView.connect_point_picking`; call `disconnect` to remove the mouse callbacks.
    """

    def __init__(
        self,
        view: NapariLineView,
        layers: ty.Sequence[Scatter | str],
        on_hover: HoverCallback | None = None,
        on_click: PointCallback | None = None,
        on_double_click: PointCallback | None = None,
        max_px: float = 8.0,
    ) -> None:
        self.view = view
        self.layers = layers
        self.on_hover = on_hover
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.max_px = max_px
        self._tooltip = ""
        self._click_callback: ty.Callable | None = None
        viewer = view.viewer
        if on_hover is not None:
            viewer.mouse_move_callbacks.append(self._on_move)
        if on_click is not None:
            self._click_callback = view.connect_click(self._on_click)
        if on_double_click is not None:
            viewer.mouse_double_click_callbacks.append(self._on_double_click)

    @property
    def layers(self) -> list[Scatter]:
        """Scatter layers whose points are picked."""
        return [layer for layer in self._layers if layer in self.view.viewer.layers]

    @layers.setter
    def layers(self, layers: ty.Sequence[Scatter | str]) -> None:
        viewer_layers = self.view.viewer.layers
        self._layers = [viewer_layers[layer] if isinstance(layer, str) else layer for layer in layers]

    def pick(self, x: float, y: float) -> tuple[Scatter, int] | None:
        """Return the scatter layer and point index at (`x`, `y`) in data coordinates, if any."""
        return nearest_point(self.view, self.layers, x, y, self.max_px)

    def _pick_event(self, event: ty.Any) -> tuple[Scatter, int] | None:
        if event.position is None:
            return None
        y, x = event.position[-2:]
        return self.pick(float(x), float(y))

    def _on_move(self, _viewer: ty.Any, event: ty.Any) -> None:
        hit = self._pick_event(event)
        text = None if hit is None or self.on_hover is None else self.on_hover(*hit)
        if not text:
            if self._tooltip:
                self._tooltip = ""
                QToolTip.hideText()
            return
        if text != self._tooltip:
            self._tooltip = text
            QToolTip.showText(QCursor.pos(), text, self.view.widget.canvas.native)

    def _on_click(self, x: float, y: float) -> None:
        hit = self.pick(x, y)
        if hit is not None and self.on_click is not None:
            self.on_click(*hit)

    def _on_double_click(self, _viewer: ty.Any, event: ty.Any) -> None:
        if event.button != 1:
            return
        hit = self._pick_event(event)
        if hit is not None and self.on_double_click is not None:
            self.on_double_click(*hit)

    def disconnect(self) -> None:
        """Remove the mouse callbacks and hide the tooltip."""
        viewer = self.view.viewer
        with suppress(ValueError):
            viewer.mouse_move_callbacks.remove(self._on_move)
        with suppress(ValueError):
            viewer.mouse_double_click_callbacks.remove(self._on_double_click)
        if self._click_callback is not None:
            self.view.disconnect_click(self._click_callback)
            self._click_callback = None
        if self._tooltip:
            self._tooltip = ""
            QToolTip.hideText()
