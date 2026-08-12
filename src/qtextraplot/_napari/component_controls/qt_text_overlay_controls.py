"""Text overlay model controls."""

from __future__ import annotations

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFormLayout, QWidget

from qtextraplot._napari._constants import TEXT_POSITION_TRANSLATIONS
from qtextraplot._napari._enums import ViewerType


class QtTextOverlayControls(QtFramelessPopup):
    """Popup to control the viewer text overlay."""

    def __init__(self, viewer: ViewerType, parent: QWidget | None = None) -> None:
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("text_overlay")
        self.setMouseTracking(True)

        self.viewer.text_overlay.events.visible.connect(self._on_visible_change)
        self.viewer.text_overlay.events.color.connect(self._on_color_change)
        self.viewer.text_overlay.events.box.connect(self._on_box_change)
        self.viewer.text_overlay.events.box_color.connect(self._on_box_color_change)
        self.viewer.text_overlay.events.position.connect(self._on_position_change)
        self.viewer.text_overlay.events.font_size.connect(self._on_font_size_change)
        self.viewer.text_overlay.events.text.connect(self._on_text_change)
        self._on_visible_change()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide text",
            value=self.viewer.text_overlay.visible,
            func=self.on_change_visible,
        )

        self.text_edit = hp.make_line_edit(self, self.viewer.text_overlay.text, placeholder="Text...")
        self.text_edit.textChanged.connect(self.on_change_text)

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, TEXT_POSITION_TRANSLATIONS, self.viewer.text_overlay.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.text_overlay.color)
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.box_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide text background",
            value=self.viewer.text_overlay.box,
            func=self.on_change_box,
        )
        self.box_color_swatch = QColorSwatchEdit(
            self,
            initial_color=self.viewer.text_overlay.box_color,
            tooltip="Click to set the text background color.",
        )
        self.box_color_swatch.color_changed.connect(self.on_change_box_color)

        self.font_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            value=self.viewer.text_overlay.font_size,
            func=self.on_change_font_size,
        )

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Text overlay controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Text"), self.text_edit)
        layout.addRow(hp.make_label(self, "Text position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Show box"), self.box_checkbox)
        layout.addRow(hp.make_label(self, "Box color"), self.box_color_swatch)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self) -> None:
        """Update visibility checkbox."""
        self.viewer.text_overlay.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.visible.blocked():
            self.visible_checkbox.setChecked(self.viewer.text_overlay.visible)
        hp.disable_widgets(
            self.color_swatch,
            self.box_checkbox,
            self.box_color_swatch,
            self.text_edit,
            self.position_combobox,
            self.font_size_spinbox,
            disabled=not self.viewer.text_overlay.visible,
        )
        self._update_box_color_enabled()

    def on_change_box(self) -> None:
        """Update text background visibility."""
        self.viewer.text_overlay.box = self.box_checkbox.isChecked()

    def _on_box_change(self, _event=None) -> None:
        """Synchronize text background visibility from the model."""
        with self.viewer.text_overlay.events.box.blocked():
            self.box_checkbox.setChecked(self.viewer.text_overlay.box)
        self._update_box_color_enabled()

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_box_color(self, color: np.ndarray) -> None:
        """Update the text background color."""
        self.viewer.text_overlay.box_color = color

    def _on_box_color_change(self, _event=None) -> None:
        """Synchronize the text background color from the model."""
        with hp.qt_signals_blocked(self.box_color_swatch):
            self.box_color_swatch.setColor(self.viewer.text_overlay.box_color)

    def _update_box_color_enabled(self) -> None:
        """Enable box color editing only while the background is displayed."""
        enabled = self.viewer.text_overlay.visible and self.viewer.text_overlay.box
        self.box_color_swatch.setEnabled(enabled)

    def on_change_text(self) -> None:
        """Update visibility checkbox."""
        self.viewer.text_overlay.text = self.text_edit.text()

    def _on_text_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.text.blocked():
            self.text_edit.setText(self.viewer.text_overlay.text)

    def on_change_position(self) -> None:
        """Update visibility checkbox."""
        self.viewer.text_overlay.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.position.blocked():
            hp.set_combobox_current_index(self.position_combobox, self.viewer.text_overlay.position)

    def on_change_font_size(self) -> None:
        """Update visibility checkbox."""
        self.viewer.text_overlay.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.font_size.blocked():
            self.font_size_spinbox.setValue(self.viewer.text_overlay.font_size)

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_color(self, color: np.ndarray) -> None:
        """Update edge color of layer model from color picker user input."""
        self.viewer.text_overlay.color = color

    def _on_color_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.viewer.text_overlay.color)

    def close(self) -> bool:
        """Disconnect events when widget is closing."""
        events = self.viewer.text_overlay.events
        events.visible.disconnect(self._on_visible_change)
        events.color.disconnect(self._on_color_change)
        events.box.disconnect(self._on_box_change)
        events.box_color.disconnect(self._on_box_color_change)
        events.position.disconnect(self._on_position_change)
        events.font_size.disconnect(self._on_font_size_change)
        events.text.disconnect(self._on_text_change)
        return super().close()
