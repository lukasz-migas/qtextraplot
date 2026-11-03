"""Scene and canvas axes overlay controls."""

from __future__ import annotations

import qtextra.helpers as hp
from napari.components.overlays import CanvasAxesOverlay, SceneAxesOverlay
from qtpy.QtWidgets import QFormLayout, QWidget

from qtextraplot._napari._constants import POSITION_TRANSLATIONS
from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.component_controls._qt_overlay_controls_base import QtOverlayControlsBase
from qtextraplot._napari.widgets.qt_font_size import QtFontSizeWidget
from qtextraplot._napari.widgets.qt_optional_color import QtOptionalColorWidget


class QtAxesControls(QtOverlayControlsBase):
    """Popup to control the scene axes and the canvas (orientation) axes."""

    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        super().__init__(viewer, parent=parent)
        self.setObjectName("axes")

    @property
    def scene_axes(self) -> SceneAxesOverlay:
        """Axes drawn at the world origin."""
        return self.viewer.scene.overlays.axes

    @property
    def canvas_axes(self) -> CanvasAxesOverlay:
        """Axes pinned to a corner of the canvas, showing camera orientation."""
        return self.viewer.canvas.overlays.axes

    def _make_style_widgets(self, overlay: SceneAxesOverlay | CanvasAxesOverlay) -> dict[str, QWidget]:
        """Widgets for the fields shared by both axes overlays."""
        return {
            "labels": self._bind(overlay, "labels", hp.make_checkbox(self, "", "Show axis labels")),
            "colored": self._bind(overlay, "colored", hp.make_checkbox(self, "", "Color each axis differently")),
            "dashed": self._bind(overlay, "dashed", hp.make_checkbox(self, "", "Use a different dash style per axis")),
            "arrows": self._bind(overlay, "arrows", hp.make_checkbox(self, "", "Show arrowheads")),
            "font_size": self._bind(overlay, "font_size", QtFontSizeWidget(self)),
        }

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.scene_visible_checkbox = self._bind(
            self.scene_axes,
            "visible",
            hp.make_checkbox(self, "", "Show/hide axes at the world origin"),
        )
        self.scene_widgets = self._make_style_widgets(self.scene_axes)
        self._bind_enabled(self.scene_axes, *self.scene_widgets.values())

        self.canvas_visible_checkbox = self._bind(
            self.canvas_axes,
            "visible",
            hp.make_checkbox(self, "", "Show/hide orientation axes in a canvas corner"),
        )
        self.canvas_widgets = self._make_style_widgets(self.canvas_axes)
        self.canvas_widgets["size"] = self._bind(
            self.canvas_axes,
            "size",
            hp.make_double_slider_with_text(self, 20, 300, step_size=10, n_decimals=0),
        )
        position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(position_combobox, POSITION_TRANSLATIONS, self.canvas_axes.position)
        self.canvas_widgets["position"] = self._bind(self.canvas_axes, "position", position_combobox)
        self.canvas_widgets["box"] = self._bind(
            self.canvas_axes,
            "box",
            hp.make_checkbox(self, "", "Show background box"),
        )
        self.canvas_widgets["box_color"] = self._bind(
            self.canvas_axes,
            "box_color",
            QtOptionalColorWidget(self, fallback="black", auto_tooltip="Use the canvas background color."),
        )
        self._bind_enabled(self.canvas_axes, *self.canvas_widgets.values())

        layout = hp.make_form_layout(parent=self, margin=(6, 6, 6, 6))
        layout.addRow(self._make_move_handle("Axes controls"))
        layout.addRow(hp.make_h_line_with_text("Scene axes", self))
        layout.addRow(hp.make_label(self, "Visible"), self.scene_visible_checkbox)
        self._add_style_rows(layout, self.scene_widgets)
        layout.addRow(hp.make_h_line_with_text("Canvas axes", self))
        layout.addRow(hp.make_label(self, "Visible"), self.canvas_visible_checkbox)
        self._add_style_rows(layout, self.canvas_widgets)
        layout.addRow(hp.make_label(self, "Size"), self.canvas_widgets["size"])
        layout.addRow(hp.make_label(self, "Position"), self.canvas_widgets["position"])
        layout.addRow(hp.make_label(self, "Show box"), self.canvas_widgets["box"])
        layout.addRow(hp.make_label(self, "Box color"), self.canvas_widgets["box_color"])
        layout.setSpacing(2)
        return layout

    def _add_style_rows(self, layout: QFormLayout, widgets: dict[str, QWidget]) -> None:
        layout.addRow(hp.make_label(self, "Labels"), widgets["labels"])
        layout.addRow(hp.make_label(self, "Colored"), widgets["colored"])
        layout.addRow(hp.make_label(self, "Dashed"), widgets["dashed"])
        layout.addRow(hp.make_label(self, "Arrows"), widgets["arrows"])
        layout.addRow(hp.make_label(self, "Font size"), widgets["font_size"])
