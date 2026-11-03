"""Controls for napari's cursor-following crosshair overlay."""

from __future__ import annotations

import qtextra.helpers as hp
from napari.components.overlays import CrosshairOverlay
from qtpy.QtWidgets import QFormLayout, QWidget

from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.component_controls._qt_overlay_controls_base import QtOverlayControlsBase
from qtextraplot._napari.widgets.qt_optional_color import QtOptionalColorWidget


class QtCursorCrosshairControls(QtOverlayControlsBase):
    """Popup to control the crosshair that follows the cursor."""

    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        super().__init__(viewer, parent=parent)
        self.setObjectName("cursor_crosshair")

    @property
    def overlay(self) -> CrosshairOverlay:
        """Cursor crosshair overlay."""
        return self.viewer.scene.overlays.crosshair

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = self._bind(
            self.overlay,
            "visible",
            hp.make_checkbox(self, "", "Show/hide the cursor crosshair"),
        )
        self.color_widget = self._bind(
            self.overlay,
            "color",
            QtOptionalColorWidget(self, auto_text="Axis colors", auto_tooltip="Color each line like its axis."),
        )
        self.gap_slider = self._bind(
            self.overlay,
            "gap",
            hp.make_slider_with_text(self, 1, 100, tooltip="Gap at the center, in pixels."),
        )
        self.opacity_slider = self._bind(
            self.overlay,
            "opacity",
            hp.make_double_slider_with_text(self, 0, 1, step_size=0.05, n_decimals=2),
        )
        self._bind_enabled(self.overlay, self.color_widget, self.gap_slider, self.opacity_slider)

        layout = hp.make_form_layout(parent=self, margin=(6, 6, 6, 6))
        layout.addRow(self._make_move_handle("Cursor crosshair controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_widget)
        layout.addRow(hp.make_label(self, "Center gap"), self.gap_slider)
        layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        layout.setSpacing(2)
        return layout
