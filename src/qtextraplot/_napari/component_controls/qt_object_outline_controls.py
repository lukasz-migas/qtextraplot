"""Object outline overlay controls."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QComboBox, QFormLayout

from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.components.overlays.object_outlines import ObjectOutlinesOverlay


class QtObjectOutlineControls(QtFramelessPopup):
    """Popup to control object outline overlays."""

    def __init__(self, viewer: ViewerType, parent=None):
        self.viewer = viewer
        self._selected_overlay: ObjectOutlinesOverlay | None = None

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("object_outlines")
        self.setMouseTracking(True)

        self.viewer._overlays.events.added.connect(self._on_overlay_collection_change)
        self.viewer._overlays.events.removed.connect(self._on_overlay_collection_change)
        self.viewer._overlays.events.changed.connect(self._on_overlay_collection_change)
        self._refresh_overlay_combo()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.overlay_combobox = QComboBox(self)
        self.overlay_combobox.currentIndexChanged.connect(self.on_change_overlay)

        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide selected object outline overlay",
            value=False,
            func=self.on_change_visible,
        )
        self.closed_checkbox = hp.make_checkbox(
            self,
            "",
            "Close outline paths",
            value=True,
            func=self.on_change_closed,
        )
        self.width_spinbox = hp.make_double_slider_with_text(
            self,
            0.5,
            20.0,
            step_size=0.5,
            value=1.0,
            func=self.on_change_width,
        )
        self.color_swatch = QColorSwatchEdit(self, initial_color="white")
        self.color_swatch.color_changed.connect(self.on_change_color)
        self.clear_button = hp.make_btn(
            self,
            "Clear",
            tooltip="Clear selected object outline overlay",
            func=self.on_clear_selected_overlay,
        )

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Object outline controls"))
        layout.addRow(hp.make_label(self, "Overlay"), self.overlay_combobox)
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Closed paths"), self.closed_checkbox)
        layout.addRow(hp.make_label(self, "Line width"), self.width_spinbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Remove"), self.clear_button)
        layout.setSpacing(2)
        return layout

    def _object_outline_overlays(self) -> dict[str, ObjectOutlinesOverlay]:
        """Return current object outline overlays."""
        return self.viewer.object_outline_overlays()

    def _current_overlay_name(self) -> str | None:
        """Return the selected overlay name."""
        if self.overlay_combobox.currentIndex() < 0:
            return None
        return ty.cast(str, self.overlay_combobox.currentData())

    def _current_overlay(self) -> ObjectOutlinesOverlay | None:
        """Return the selected overlay."""
        overlay_name = self._current_overlay_name()
        if overlay_name is None:
            return None
        return self._object_outline_overlays().get(overlay_name)

    def _connect_selected_overlay(self, overlay: ObjectOutlinesOverlay | None) -> None:
        if self._selected_overlay is not None:
            disconnect_events(self._selected_overlay.events, self)
            for outline in self._selected_overlay.outlines:
                disconnect_events(outline.events, self)
        self._selected_overlay = overlay
        if overlay is None:
            return
        overlay.events.visible.connect(self._on_visible_change)
        overlay.events.closed.connect(self._on_closed_change)
        overlay.events.outlines.connect(self._on_outlines_change)
        for outline in overlay.outlines:
            outline.events.width.connect(self._on_width_change)
            outline.events.color.connect(self._on_color_change)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.visible_checkbox.setEnabled(enabled)
        self.closed_checkbox.setEnabled(enabled)
        self.width_spinbox.setEnabled(enabled)
        self.color_swatch.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

    def _refresh_overlay_combo(self) -> None:
        selected_name = self._current_overlay_name()
        overlays = self._object_outline_overlays()
        if selected_name not in overlays:
            selected_name = next(iter(overlays), None)

        with hp.qt_signals_blocked(self.overlay_combobox):
            self.overlay_combobox.clear()
            for name in overlays:
                self.overlay_combobox.addItem(name, name)
            if selected_name is not None:
                index = self.overlay_combobox.findData(selected_name)
                self.overlay_combobox.setCurrentIndex(index)

        self._connect_selected_overlay(overlays.get(selected_name) if selected_name is not None else None)
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        overlay = self._selected_overlay
        enabled = overlay is not None
        self._set_controls_enabled(enabled)
        if overlay is None:
            return

        with overlay.events.visible.blocker(), hp.qt_signals_blocked(self.visible_checkbox):
            self.visible_checkbox.setChecked(overlay.visible)
        with overlay.events.closed.blocker(), hp.qt_signals_blocked(self.closed_checkbox):
            self.closed_checkbox.setChecked(overlay.closed)
        self._on_width_change()
        self._on_color_change()

    def _on_overlay_collection_change(self, _event=None) -> None:
        """Refresh overlay selection when overlays are added or removed."""
        self._refresh_overlay_combo()

    def on_change_overlay(self) -> None:
        """Update controls when the selected overlay changes."""
        self._connect_selected_overlay(self._current_overlay())
        self._refresh_controls()

    def on_change_visible(self) -> None:
        """Update selected overlay visibility."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        overlay = self._selected_overlay
        if overlay is not None:
            with hp.qt_signals_blocked(self.visible_checkbox):
                self.visible_checkbox.setChecked(overlay.visible)

    def on_change_closed(self) -> None:
        """Update selected overlay closed-path state."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.closed = self.closed_checkbox.isChecked()

    def _on_closed_change(self, _event=None) -> None:
        """Update closed-path checkbox."""
        overlay = self._selected_overlay
        if overlay is not None:
            with hp.qt_signals_blocked(self.closed_checkbox):
                self.closed_checkbox.setChecked(overlay.closed)

    def on_change_width(self) -> None:
        """Apply line width to all outlines in the selected overlay."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        width = self.width_spinbox.value()
        for outline in overlay.outlines:
            outline.width = width

    def _on_width_change(self, _event=None) -> None:
        """Update width control."""
        overlay = self._selected_overlay
        if overlay is None or not overlay.outlines:
            return
        with hp.qt_signals_blocked(self.width_spinbox):
            self.width_spinbox.setValue(overlay.outlines[0].width)

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_color(self, color: np.ndarray) -> None:
        """Apply color to all outlines in the selected overlay."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        for outline in overlay.outlines:
            outline.color = color

    def _on_color_change(self, _event=None) -> None:
        """Update color control."""
        overlay = self._selected_overlay
        if overlay is None or not overlay.outlines:
            return
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(overlay.outlines[0].color)

    def _on_outlines_change(self, _event=None) -> None:
        """Reconnect outline events and refresh controls."""
        self._connect_selected_overlay(self._selected_overlay)
        self._refresh_controls()

    def on_clear_selected_overlay(self) -> None:
        """Clear the selected overlay."""
        overlay_name = self._current_overlay_name()
        if overlay_name is not None:
            self.viewer.clear_object_outlines(overlay_name)

    def close(self) -> None:
        """Disconnect events when widget is closing."""
        self._connect_selected_overlay(None)
        disconnect_events(self.viewer._overlays.events, self)
        super().close()
