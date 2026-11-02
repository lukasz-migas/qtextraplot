"""Controls for napari's coordinate grid (ticks and gridlines) overlay."""

from __future__ import annotations

import qtextra.helpers as hp
from napari.components.overlays import CoordinateGridOverlay
from qtpy.QtWidgets import QFormLayout, QWidget

from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.component_controls._qt_overlay_controls_base import QtOverlayControlsBase
from qtextraplot._napari.widgets.qt_font_size import QtFontSizeWidget
from qtextraplot._napari.widgets.qt_optional_color import QtOptionalColorWidget


class QtCoordinateGridControls(QtOverlayControlsBase):
    """Popup to control the coordinate grid drawn over the scene."""

    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        super().__init__(viewer, parent=parent)
        self.setObjectName("coordinate_grid")

    @property
    def overlay(self) -> CoordinateGridOverlay:
        """Coordinate grid overlay."""
        return self.viewer.scene.overlays.coordinate_grid

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = self._bind(
            self.overlay,
            "visible",
            hp.make_checkbox(self, "", "Show/hide the coordinate grid"),
        )
        self.color_widget = self._bind(
            self.overlay,
            "color",
            QtOptionalColorWidget(self, auto_tooltip="Contrast the grid with the canvas background."),
        )
        self.tick_labels_checkbox = self._bind(
            self.overlay,
            "tick_labels",
            hp.make_checkbox(self, "", "Show tick labels"),
        )
        self.axis_labels_checkbox = self._bind(
            self.overlay,
            "axis_labels",
            hp.make_checkbox(self, "", "Show axis labels"),
        )
        self.n_ticks_slider = self._bind(
            self.overlay,
            "n_ticks",
            hp.make_slider_with_text(self, 2, 20, tooltip="Approximate number of ticks per axis."),
        )
        self.font_size_widget = self._bind(self.overlay, "font_size", QtFontSizeWidget(self))
        self.opacity_slider = self._bind(
            self.overlay,
            "opacity",
            hp.make_double_slider_with_text(self, 0, 1, step_size=0.05, n_decimals=2),
        )
        self._bind_enabled(
            self.overlay,
            self.color_widget,
            self.tick_labels_checkbox,
            self.axis_labels_checkbox,
            self.n_ticks_slider,
            self.font_size_widget,
            self.opacity_slider,
        )

        layout = hp.make_form_layout(parent=self, margin=(6, 6, 6, 6))
        layout.addRow(self._make_move_handle("Coordinate grid controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_widget)
        layout.addRow(hp.make_label(self, "Tick labels"), self.tick_labels_checkbox)
        layout.addRow(hp.make_label(self, "Axis labels"), self.axis_labels_checkbox)
        layout.addRow(hp.make_label(self, "Number of ticks"), self.n_ticks_slider)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_widget)
        layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        layout.setSpacing(2)
        return layout
