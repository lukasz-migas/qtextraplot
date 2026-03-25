"""ColorBar model controls."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

from qtextraplot._napari._constants import POSITION_TRANSLATIONS
from qtextraplot._napari._enums import ViewerType

if ty.TYPE_CHECKING:
    from napari.layers import Image


class QtColorBarControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerType, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("colorbar")
        self.setMouseTracking(True)

    def _layer_iter(self) -> ty.Generator[Image, None, None]:
        for layer in self.viewer.layers:
            if hasattr(layer, "colorbar") and hasattr(layer, "rgb") and not layer.rgb:
                yield layer

    def _get_common_value(self, attr: str, default: ty.Any) -> ty.Any:
        """Get a common value from attribute."""
        values = set()
        for layer in self._layer_iter():
            value = getattr(layer.colorbar, attr)
            if attr == "color" and value is not None:
                value = tuple(value)
            values.add(value)
        if values:
            value = values.pop()
            if value is not None:
                return value
        return default

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide colorbar",
            value=self._get_common_value("visible", False),
            func=self.on_change_visible,
        )
        self.position_combobox = hp.make_combobox(
            self,
            data=POSITION_TRANSLATIONS,
            value=self._get_common_value("position", "top_right"),
            func=self.on_change_position,
        )

        # tick and text controls
        print(self._get_common_value("color", "white"))
        self.text_color_swatch = QColorSwatchEdit(self, initial_color=self._get_common_value("color", "white"))
        self.text_color_swatch.color_changed.connect(self.on_change_border_color)

        self.text_size_spin = hp.make_double_slider_with_text(
            self,
            4,
            24,
            step_size=1,
            value=self._get_common_value("font_size", 10),
            func=self.on_change_tick_font_size,
        )
        self.tick_length_spin = hp.make_double_slider_with_text(
            self,
            0,
            20,
            step_size=1,
            value=self._get_common_value("tick_length", 5),
            func=self.on_change_tick_length,
        )

        # self.box_visible_check = hp.make_checkbox(
        #     self,
        #     "",
        #     "Show/hide box around colorbar",
        #     value=False,
        #     func=self.on_change_box_visible,
        # )
        # self.box_color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.color_bar.label_color)
        # self.box_color_swatch.color_changed.connect(self.on_change_box_color)

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Colorbar controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Edge and text color"), self.text_color_swatch)
        layout.addRow(hp.make_label(self, "Text size"), self.text_size_spin)
        layout.addRow(hp.make_label(self, "Tick size"), self.tick_length_spin)
        # layout.addRow(hp.make_label(self, "Box visible"), self.box_visible_check)
        # layout.addRow(hp.make_label(self, "Box color"), self.box_color_swatch)
        layout.setSpacing(2)
        return layout

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        visible = self.visible_checkbox.isChecked()
        hp.disable_widgets(
            self.position_combobox,
            self.text_color_swatch,
            self.text_size_spin,
            self.tick_length_spin,
            # self.box_visible_check,
            # self.box_color_swatch,
            disabled=not visible,
        )

    def on_change_visible(self):
        """Update visibility checkbox."""
        visible = self.visible_checkbox.isChecked()
        for layer in self._layer_iter():
            layer.colorbar.visible = visible

    def on_change_position(self):
        """Update visibility checkbox."""
        position = self.position_combobox.currentData()
        for layer in self._layer_iter():
            # TODO: position is not updated when changed, but only after changing another property
            # TODO: once napari fixes the issue, we can remove this line
            layer.colorbar.position = position
            layer.colorbar.font_size += 0.01

    def on_change_border_color(self, color: str):
        """Update edge color of layer model from color picker user input."""
        for layer in self._layer_iter():
            layer.colorbar.color = color

    def on_change_tick_font_size(self):
        """Update visibility checkbox."""
        value = self.text_size_spin.value()
        for layer in self._layer_iter():
            layer.colorbar.font_size = value

    def on_change_tick_length(self):
        """Update visibility checkbox."""
        value = self.tick_length_spin.value()
        for layer in self._layer_iter():
            layer.colorbar.tick_length = value

    def on_change_box_visible(self):
        """Update visibility checkbox."""
        visible = self.box_visible_check.isChecked()
        for layer in self._layer_iter():
            layer.colorbar.box = visible

    def on_change_box_color(self, color: str):
        """Update edge color of layer model from color picker user input."""
        for layer in self._layer_iter():
            layer.colorbar.box_color = color
