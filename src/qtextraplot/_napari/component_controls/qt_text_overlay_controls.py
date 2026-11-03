"""ScaleBar model controls."""

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.components.overlays import TextOverlay
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFormLayout

from qtextraplot._napari._constants import TEXT_POSITION_TRANSLATIONS
from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.widgets.qt_font_size import QtFontSizeWidget


class QtTextOverlayControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerType, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("text_overlay")
        self.setMouseTracking(True)

        self.overlay.events.visible.connect(self._on_visible_change)
        self.overlay.events.color.connect(self._on_color_change)
        self.overlay.events.position.connect(self._on_position_change)
        self.overlay.events.font_size.connect(self._on_font_size_change)
        self.overlay.events.text.connect(self._on_text_change)
        self._on_visible_change()

    @property
    def overlay(self) -> TextOverlay:
        """Text overlay."""
        return self.viewer.canvas.overlays.text

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide text",
            value=self.overlay.visible,
            func=self.on_change_visible,
        )

        self.text_edit = hp.make_line_edit(self, self.overlay.text, placeholder="Text...")
        self.text_edit.textChanged.connect(self.on_change_text)

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, TEXT_POSITION_TRANSLATIONS, self.overlay.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.color_swatch = QColorSwatchEdit(self, initial_color=self.overlay.color)
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.font_size_spinbox = QtFontSizeWidget(self, value=self.overlay.font_size, func=self.on_change_font_size)

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Text overlay controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Text"), self.text_edit)
        layout.addRow(hp.make_label(self, "Text position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self):
        """Update visibility checkbox."""
        self.overlay.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.overlay.events.visible.blocked():
            self.visible_checkbox.setChecked(self.overlay.visible)
        hp.disable_widgets(
            self.color_swatch,
            self.text_edit,
            self.position_combobox,
            self.font_size_spinbox,
            disabled=not self.overlay.visible,
        )

    def on_change_text(self):
        """Update visibility checkbox."""
        self.overlay.text = self.text_edit.text()

    def _on_text_change(self, _event=None):
        """Update visibility checkbox."""
        with self.overlay.events.text.blocked():
            self.text_edit.setText(self.overlay.text)

    def on_change_position(self):
        """Update visibility checkbox."""
        self.overlay.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None):
        """Update visibility checkbox."""
        with self.overlay.events.position.blocked():
            hp.set_combobox_current_index(self.position_combobox, self.overlay.position)

    def on_change_font_size(self):
        """Update visibility checkbox."""
        self.overlay.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None):
        """Update visibility checkbox."""
        with self.overlay.events.font_size.blocked():
            self.font_size_spinbox.setValue(self.overlay.font_size)

    @Slot(np.ndarray)  # type: ignore
    def on_change_color(self, color: np.ndarray):
        """Update edge color of layer model from color picker user input."""
        self.overlay.color = color

    def _on_color_change(self, _event=None):
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.overlay.color)

    def close(self):
        """Disconnect events when widget is closing."""
        events = self.overlay.events
        events.visible.disconnect(self._on_visible_change)
        events.color.disconnect(self._on_color_change)
        events.position.disconnect(self._on_position_change)
        events.font_size.disconnect(self._on_font_size_change)
        events.text.disconnect(self._on_text_change)
        super().close()
