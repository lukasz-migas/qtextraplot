"""Object outline visuals."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispySceneOverlay
from napari.utils.events import disconnect_events
from vispy.scene.visuals import Compound, Line

from qtextraplot._napari.components.overlays.object_outlines import ObjectOutline, ObjectOutlinesOverlay

if ty.TYPE_CHECKING:
    from napari.layers import Layer

TARGET_LAYER_EVENTS = ("data", "set_data", "scale", "translate", "rotate", "shear", "affine")


def outline_data_to_scene(data: np.ndarray, layer: Layer, displayed: ty.Sequence[int]) -> np.ndarray:
    """Convert outline data coordinates to Vispy scene coordinates."""
    if data.size == 0:
        return np.empty((0, 3), dtype=float)

    world = np.asarray([layer.data_to_world(point) for point in data], dtype=float)
    displayed_axes = tuple(displayed)
    if not displayed_axes:
        return np.empty((0, 3), dtype=float)

    n_required_dims = max(displayed_axes) + 1
    if world.shape[1] < n_required_dims:
        n_pad = n_required_dims - world.shape[1]
        world = np.pad(world, ((0, 0), (n_pad, 0)), mode="constant")

    scene = np.zeros((len(world), 3), dtype=float)
    displayed_world = world[:, list(displayed_axes)]
    scene[:, : len(displayed_axes)] = displayed_world[:, ::-1]
    return scene


def points_to_segments(points: np.ndarray, closed: bool) -> np.ndarray:
    """Convert ordered points to flattened line segments."""
    if len(points) < 2:
        return np.empty((0, points.shape[1] if points.ndim == 2 else 3), dtype=float)

    starts = points[:-1]
    ends = points[1:]
    if closed:
        starts = np.concatenate([starts, points[-1:]], axis=0)
        ends = np.concatenate([ends, points[:1]], axis=0)
    segments = np.stack([starts, ends], axis=1)
    return segments.reshape(-1, points.shape[1])


class VispyObjectOutlinesOverlay(ViewerOverlayMixin, VispySceneOverlay):
    """Object outline visual."""

    def __init__(self, viewer, overlay: ObjectOutlinesOverlay, parent=None):
        super().__init__(
            node=Compound([], parent=parent),
            viewer=viewer,
            overlay=overlay,
            parent=parent,
        )
        self._line_nodes: list[Line] = []
        self._target_layer: Layer | None = None
        self._connected_outlines: tuple[ObjectOutline, ...] = ()

        self.overlay.events.outlines.connect(self._on_outlines_change)
        self.overlay.events.closed.connect(self._on_data_change)
        self.overlay.events.target_layer.connect(self._on_target_layer_change)
        self.viewer.dims.events.displayed.connect(self._on_data_change)
        self.viewer.dims.events.ndisplay.connect(self._on_data_change)
        self.viewer.layers.events.inserted.connect(self._on_target_layer_change)
        self.viewer.layers.events.removed.connect(self._on_target_layer_change)
        self.viewer.layers.events.changed.connect(self._on_target_layer_change)

        self._connect_outline_events()
        self._connect_target_layer_events()
        self.reset()

    def _get_target_layer(self) -> Layer | None:
        if self.overlay.target_layer is None:
            return None
        with suppress(KeyError):
            return self.viewer.layers[self.overlay.target_layer]
        return None

    def _connect_target_layer_events(self) -> None:
        layer = self._get_target_layer()
        if layer is self._target_layer:
            return
        if self._target_layer is not None:
            disconnect_events(self._target_layer.events, self)
        self._target_layer = layer
        if layer is None:
            return
        for event_name in TARGET_LAYER_EVENTS:
            with suppress(AttributeError, KeyError):
                getattr(layer.events, event_name).connect(self._on_data_change)

    def _disconnect_outline_events(self) -> None:
        for outline in self._connected_outlines:
            disconnect_events(outline.events, self)
        self._connected_outlines = ()

    def _connect_outline_events(self) -> None:
        self._disconnect_outline_events()
        for outline in self.overlay.outlines:
            outline.events.data.connect(self._on_data_change)
            outline.events.color.connect(self._on_data_change)
            outline.events.width.connect(self._on_data_change)
        self._connected_outlines = tuple(self.overlay.outlines)

    def _on_outlines_change(self, _evt=None) -> None:
        """Refresh line event connections and rendered data."""
        self._connect_outline_events()
        self._on_data_change()

    def _on_target_layer_change(self, _evt=None) -> None:
        """Refresh target layer event connections and rendered data."""
        self._connect_target_layer_events()
        self._on_data_change()

    def _clear_lines(self) -> None:
        while self._line_nodes:
            line = self._line_nodes.pop()
            self.node.remove_subvisual(line)

    def _ensure_line_count(self, count: int) -> None:
        while len(self._line_nodes) > count:
            line = self._line_nodes.pop()
            self.node.remove_subvisual(line)
        while len(self._line_nodes) < count:
            line = Line(connect="segments", method="gl")
            self.node.add_subvisual(line)
            self._line_nodes.append(line)

    def _line_groups(self, layer: Layer) -> list[tuple[float, np.ndarray, np.ndarray]]:
        groups: dict[float, list[tuple[np.ndarray, np.ndarray]]] = {}
        for outline in self.overlay.outlines:
            points = outline_data_to_scene(outline.data, layer, self.viewer.dims.displayed)
            segments = points_to_segments(points, closed=self.overlay.closed)
            if len(segments) == 0:
                continue
            color = np.broadcast_to(np.asarray(outline.color, dtype=float), (len(segments), 4)).copy()
            groups.setdefault(outline.width, []).append((segments, color))

        return [
            (
                width,
                np.concatenate([positions for positions, _colors in items]),
                np.concatenate([colors for _, colors in items]),
            )
            for width, items in groups.items()
        ]

    def _on_data_change(self, _evt=None) -> None:
        """Change outline data."""
        layer = self._get_target_layer()
        if layer is None or not self.overlay.outlines:
            self._clear_lines()
            return

        groups = self._line_groups(layer)
        self._ensure_line_count(len(groups))
        for line, (width, positions, colors) in zip(self._line_nodes, groups, strict=True):
            line.set_data(pos=positions, color=colors, width=width)
        self._on_blending_change()
        self.node.update()

    def reset(self) -> None:
        super().reset()
        self._on_data_change()

    def close(self) -> None:
        self._disconnect_outline_events()
        if self._target_layer is not None:
            disconnect_events(self._target_layer.events, self)
        disconnect_events(self.viewer.dims.events, self)
        disconnect_events(self.viewer.layers.events, self)
        self._clear_lines()
        super().close()


__all__ = [
    "VispyObjectOutlinesOverlay",
    "outline_data_to_scene",
    "points_to_segments",
]
