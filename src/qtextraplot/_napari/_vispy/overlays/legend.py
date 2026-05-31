"""Legend canvas overlay visual."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay
from napari.utils.colormaps import ensure_colormap
from napari.utils.events import disconnect_events
from vispy.scene.visuals import Compound, Line, Markers, Rectangle, Text

from qtextraplot._napari.components.overlays.legend import LegendEntry, LegendOverlay

FALLBACK_MARKER = "square"
TEXT_WIDTH_FACTOR = 1.05
TEXT_EXTRA_PADDING_FACTOR = 1.5
MARKER_TEXT_GAP = 8.0


def legend_entry_color(entry: LegendEntry, fallback: ty.Any) -> np.ndarray:
    """Return a display color for a legend entry."""
    if entry.color is not None:
        return np.asarray(entry.color, dtype=float)
    if entry.colormap is not None:
        try:
            return np.asarray(ensure_colormap(entry.colormap).map(np.asarray([0.5]))[0], dtype=float)
        except (KeyError, TypeError, ValueError, AttributeError):
            return np.asarray(fallback, dtype=float)
    return np.asarray(fallback, dtype=float)


def legend_layout_size(overlay: LegendOverlay) -> tuple[float, float]:
    """Estimate legend canvas size from entries and style."""
    if not overlay.entries:
        return 0.0, 0.0

    labels = [entry.label for entry in overlay.entries]
    row_height = max(overlay.font_size, overlay.marker_size) + overlay.row_spacing
    marker_column_width = overlay.marker_size + MARKER_TEXT_GAP if _has_marker_column(overlay.entries) else 0.0
    text_width = max(len(label) for label in labels) * overlay.font_size * TEXT_WIDTH_FACTOR
    text_extra_padding = overlay.font_size * TEXT_EXTRA_PADDING_FACTOR
    x_size = (2 * overlay.padding) + marker_column_width + text_width + text_extra_padding
    y_size = (2 * overlay.padding) + (len(labels) * row_height) - overlay.row_spacing
    return float(x_size), float(y_size)


def _has_marker_column(entries: ty.Sequence[LegendEntry]) -> bool:
    return any(entry.marker is not None or entry.color is not None or entry.colormap is not None for entry in entries)


def _border_segments(x_size: float, y_size: float) -> np.ndarray:
    corners = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [x_size, 0.0, 0.0],
            [x_size, y_size, 0.0],
            [0.0, y_size, 0.0],
        ],
        dtype=float,
    )
    return np.asarray(
        [
            corners[0],
            corners[1],
            corners[1],
            corners[2],
            corners[2],
            corners[3],
            corners[3],
            corners[0],
        ],
        dtype=float,
    )


class VispyLegendOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Canvas-space legend visual."""

    def __init__(self, viewer, overlay: LegendOverlay, parent=None):
        self._background = Rectangle(center=(0, 0), width=1, height=1, color=(0, 0, 0, 0))
        self._border = Line(connect="segments", method="gl")
        self._text = Text(text="", pos=(0, 0, 0), anchor_x="left", anchor_y="center")
        self._markers: list[Markers] = []
        self._connected_entries: tuple[LegendEntry, ...] = ()

        node = Compound([self._background, self._border, self._text], parent=parent)
        super().__init__(node=node, viewer=viewer, overlay=overlay, parent=parent)

        self.overlay.events.entries.connect(self._on_entries_change)
        self.overlay.events.text_color.connect(self._on_data_change)
        self.overlay.events.font_size.connect(self._on_data_change)
        self.overlay.events.marker_size.connect(self._on_data_change)
        self.overlay.events.row_spacing.connect(self._on_data_change)
        self.overlay.events.padding.connect(self._on_data_change)
        self.overlay.events.background_color.connect(self._on_data_change)
        self.overlay.events.border_color.connect(self._on_data_change)
        self.overlay.events.border_width.connect(self._on_data_change)

        self._connect_entry_events()
        self.reset()

    def _connect_entry_events(self) -> None:
        self._disconnect_entry_events()
        for entry in self.overlay.entries:
            entry.events.label.connect(self._on_data_change)
            entry.events.marker.connect(self._on_data_change)
            entry.events.color.connect(self._on_data_change)
            entry.events.colormap.connect(self._on_data_change)
        self._connected_entries = tuple(self.overlay.entries)

    def _disconnect_entry_events(self) -> None:
        for entry in self._connected_entries:
            disconnect_events(entry.events, self)
        self._connected_entries = ()

    def _on_entries_change(self, _event=None) -> None:
        """Reconnect legend row events and redraw."""
        self._connect_entry_events()
        self._on_data_change()

    def _ensure_marker_count(self, count: int) -> None:
        while len(self._markers) > count:
            marker = self._markers.pop()
            self.node.remove_subvisual(marker)
        while len(self._markers) < count:
            marker = Markers(scaling="fixed")
            self.node.add_subvisual(marker)
            self._markers.append(marker)

    def _clear_visuals(self) -> None:
        self.x_size = 0.0
        self.y_size = 0.0
        self._background.width = 1
        self._background.height = 1
        self._background.color = (0, 0, 0, 0)
        self._background.visible = False
        self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)
        self._text.text = ""
        self._text.pos = (0, 0, 0)
        self._text.visible = False
        self._ensure_marker_count(0)

    def _row_positions(self) -> np.ndarray:
        row_height = max(self.overlay.font_size, self.overlay.marker_size) + self.overlay.row_spacing
        row_center = max(self.overlay.font_size, self.overlay.marker_size) / 2
        text_x = self.overlay.padding
        if _has_marker_column(self.overlay.entries):
            text_x += self.overlay.marker_size + MARKER_TEXT_GAP
        return np.asarray(
            [
                [text_x, self.overlay.padding + row_center + (index * row_height), 0.0]
                for index, _entry in enumerate(self.overlay.entries)
            ],
            dtype=float,
        )

    def _on_data_change(self, _event=None) -> None:
        """Redraw legend visual state from the overlay model."""
        if not self.overlay.entries:
            self._clear_visuals()
            self._on_position_change(None)
            self.node.update()
            return

        self.x_size, self.y_size = legend_layout_size(self.overlay)
        text_positions = self._row_positions()

        self._background.center = (self.x_size / 2, self.y_size / 2)
        self._background.width = self.x_size
        self._background.height = self.y_size
        self._background.color = self.overlay.background_color
        self._background.visible = True
        self._background.update()

        if self.overlay.border_width > 0:
            self._border.set_data(
                pos=_border_segments(self.x_size, self.y_size),
                color=self.overlay.border_color,
                width=self.overlay.border_width,
            )
        else:
            self._border.set_data(pos=np.empty((0, 3)), color=(0, 0, 0, 0), width=0)

        self._text.text = [entry.label for entry in self.overlay.entries]
        self._text.pos = text_positions
        self._text.color = self.overlay.text_color
        self._text.font_size = self.overlay.font_size
        self._text.visible = True

        marker_entries = [
            (entry, row_position)
            for entry, row_position in zip(self.overlay.entries, text_positions, strict=True)
            if entry.marker is not None or entry.color is not None or entry.colormap is not None
        ]
        self._ensure_marker_count(len(marker_entries))
        marker_x = self.overlay.padding + (self.overlay.marker_size / 2)
        for marker, (entry, row_position) in zip(self._markers, marker_entries, strict=True):
            color = legend_entry_color(entry, self.overlay.text_color)
            marker_pos = np.asarray([[marker_x, row_position[1], 0.0]], dtype=float)
            try:
                marker.set_data(
                    pos=marker_pos,
                    symbol=entry.marker or FALLBACK_MARKER,
                    size=self.overlay.marker_size,
                    face_color=color,
                    edge_color=color,
                    edge_width=0,
                )
            except ValueError:
                marker.set_data(
                    pos=marker_pos,
                    symbol=FALLBACK_MARKER,
                    size=self.overlay.marker_size,
                    face_color=color,
                    edge_color=color,
                    edge_width=0,
                )

        self._on_position_change(None)
        self._on_blending_change()
        self.node.update()

    def _on_position_change(self, _event=None) -> None:
        """Request canvas repositioning and redraw."""
        super()._on_position_change()
        self.node.update()
        with suppress(AttributeError):
            self.node.canvas.update()

    def reset(self) -> None:
        super().reset()
        self._on_data_change()

    def close(self) -> None:
        self._disconnect_entry_events()
        self._ensure_marker_count(0)
        super().close()


__all__ = [
    "VispyLegendOverlay",
    "legend_entry_color",
    "legend_layout_size",
]
