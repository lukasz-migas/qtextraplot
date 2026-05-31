"""Legend overlay controls."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.layers import Points
from napari.utils.events import disconnect_events
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QComboBox, QFormLayout

from qtextraplot._napari._constants import POSITION_TRANSLATIONS
from qtextraplot._napari._enums import ViewerType
from qtextraplot._napari.components.overlays.legend import LegendOverlay
from qtextraplot._napari.image.components.viewer_model import LEGEND_OVERLAY_NAME


class QtLegendControls(QtFramelessPopup):
    """Popup to control legend overlays."""

    def __init__(self, viewer: ViewerType, parent=None):
        self.viewer = viewer
        self._selected_overlay: LegendOverlay | None = None

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("legend")
        self.setMouseTracking(True)

        self.viewer._overlays.events.added.connect(self._on_overlay_collection_change)
        self.viewer._overlays.events.removed.connect(self._on_overlay_collection_change)
        self.viewer._overlays.events.changed.connect(self._on_overlay_collection_change)
        self.viewer.layers.events.inserted.connect(self._refresh_source_combo)
        self.viewer.layers.events.removed.connect(self._refresh_source_combo)
        self.viewer.layers.events.changed.connect(self._refresh_source_combo)
        self._refresh_overlay_combo()
        self._refresh_source_combo()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.overlay_combobox = QComboBox(self)
        self.overlay_combobox.currentIndexChanged.connect(self.on_change_overlay)

        self.visible_checkbox = hp.make_checkbox(
            self,
            "",
            "Show/hide selected legend overlay",
            value=False,
            func=self.on_change_visible,
        )
        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, POSITION_TRANSLATIONS, "top_right")
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.source_layer_combobox = QComboBox(self)
        self.generate_button = hp.make_btn(
            self,
            "From points",
            tooltip="Regenerate selected legend from a Points layer",
            func=self.on_generate_from_points,
        )
        self.auto_sync_checkbox = hp.make_checkbox(
            self,
            "",
            "Automatically refresh selected legend when its Points layer changes",
            value=False,
            func=self.on_change_auto_sync,
        )

        self.text_color_swatch = QColorSwatchEdit(self, initial_color="white")
        self.text_color_swatch.color_changed.connect(self.on_change_text_color)
        self.background_color_swatch = QColorSwatchEdit(self, initial_color=(0.0, 0.0, 0.0, 0.65))
        self.background_color_swatch.color_changed.connect(self.on_change_background_color)
        self.border_color_swatch = QColorSwatchEdit(self, initial_color=(1.0, 1.0, 1.0, 0.8))
        self.border_color_swatch.color_changed.connect(self.on_change_border_color)

        self.font_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            value=10,
            func=self.on_change_font_size,
        )
        self.marker_size_spinbox = hp.make_double_slider_with_text(
            self,
            4,
            32,
            step_size=1,
            value=10,
            func=self.on_change_marker_size,
        )
        self.padding_spinbox = hp.make_double_slider_with_text(
            self,
            0,
            24,
            step_size=1,
            value=6,
            func=self.on_change_padding,
        )
        self.row_spacing_spinbox = hp.make_double_slider_with_text(
            self,
            1,
            24,
            step_size=1,
            value=4,
            func=self.on_change_row_spacing,
        )
        self.border_width_spinbox = hp.make_double_slider_with_text(
            self,
            0,
            8,
            step_size=0.5,
            value=1,
            func=self.on_change_border_width,
        )
        self.clear_button = hp.make_btn(
            self,
            "Clear",
            tooltip="Clear selected legend overlay",
            func=self.on_clear_selected_overlay,
        )

        layout = hp.make_form_layout(parent=self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Legend controls"))
        layout.addRow(hp.make_label(self, "Overlay"), self.overlay_combobox)
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Points layer"), self.source_layer_combobox)
        layout.addRow(hp.make_label(self, "Regenerate"), self.generate_button)
        layout.addRow(hp.make_label(self, "Auto sync"), self.auto_sync_checkbox)
        layout.addRow(hp.make_label(self, "Text color"), self.text_color_swatch)
        layout.addRow(hp.make_label(self, "Text size"), self.font_size_spinbox)
        layout.addRow(hp.make_label(self, "Marker size"), self.marker_size_spinbox)
        layout.addRow(hp.make_label(self, "Padding"), self.padding_spinbox)
        layout.addRow(hp.make_label(self, "Row gap"), self.row_spacing_spinbox)
        layout.addRow(hp.make_label(self, "Background"), self.background_color_swatch)
        layout.addRow(hp.make_label(self, "Border color"), self.border_color_swatch)
        layout.addRow(hp.make_label(self, "Border width"), self.border_width_spinbox)
        layout.addRow(hp.make_label(self, "Remove"), self.clear_button)
        layout.setSpacing(2)
        return layout

    def _legend_overlays(self) -> dict[str, LegendOverlay]:
        """Return current legend overlays."""
        return self.viewer.legend_overlays()

    def _points_layers(self) -> list[Points]:
        """Return current Points layers."""
        return [ty.cast(Points, layer) for layer in self.viewer.layers if isinstance(layer, Points)]

    def _current_overlay_name(self) -> str | None:
        """Return selected legend overlay name."""
        if self.overlay_combobox.currentIndex() < 0:
            return None
        return ty.cast(str, self.overlay_combobox.currentData())

    def _current_overlay(self) -> LegendOverlay | None:
        """Return selected legend overlay."""
        overlay_name = self._current_overlay_name()
        if overlay_name is None:
            return None
        return self._legend_overlays().get(overlay_name)

    def _connect_selected_overlay(self, overlay: LegendOverlay | None) -> None:
        if self._selected_overlay is not None:
            disconnect_events(self._selected_overlay.events, self)
        self._selected_overlay = overlay
        if overlay is None:
            return
        overlay.events.visible.connect(self._on_visible_change)
        overlay.events.position.connect(self._on_position_change)
        overlay.events.source_layer.connect(self._on_source_layer_change)
        overlay.events.sync_with_source.connect(self._on_auto_sync_change)
        overlay.events.text_color.connect(self._on_text_color_change)
        overlay.events.font_size.connect(self._on_font_size_change)
        overlay.events.marker_size.connect(self._on_marker_size_change)
        overlay.events.row_spacing.connect(self._on_row_spacing_change)
        overlay.events.padding.connect(self._on_padding_change)
        overlay.events.background_color.connect(self._on_background_color_change)
        overlay.events.border_color.connect(self._on_border_color_change)
        overlay.events.border_width.connect(self._on_border_width_change)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.visible_checkbox.setEnabled(enabled)
        self.position_combobox.setEnabled(enabled)
        self.text_color_swatch.setEnabled(enabled)
        self.font_size_spinbox.setEnabled(enabled)
        self.marker_size_spinbox.setEnabled(enabled)
        self.padding_spinbox.setEnabled(enabled)
        self.row_spacing_spinbox.setEnabled(enabled)
        self.background_color_swatch.setEnabled(enabled)
        self.border_color_swatch.setEnabled(enabled)
        self.border_width_spinbox.setEnabled(enabled)
        self.auto_sync_checkbox.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

    def _refresh_overlay_combo(self) -> None:
        selected_name = self._current_overlay_name()
        overlays = self._legend_overlays()
        if selected_name not in overlays:
            selected_name = next(iter(overlays), None)

        with hp.qt_signals_blocked(self.overlay_combobox):
            self.overlay_combobox.clear()
            for name in overlays:
                self.overlay_combobox.addItem(name, name)
            if selected_name is not None:
                self.overlay_combobox.setCurrentIndex(self.overlay_combobox.findData(selected_name))

        self._connect_selected_overlay(overlays.get(selected_name) if selected_name is not None else None)
        self._refresh_controls()

    def _refresh_source_combo(self, _event=None) -> None:
        selected_name = self._selected_overlay.source_layer if self._selected_overlay is not None else None
        if self.source_layer_combobox.currentIndex() >= 0:
            selected_layer = ty.cast(Points | None, self.source_layer_combobox.currentData())
            selected_name = selected_name or (selected_layer.name if selected_layer is not None else None)

        points_layers = self._points_layers()
        with hp.qt_signals_blocked(self.source_layer_combobox):
            self.source_layer_combobox.clear()
            for layer in points_layers:
                self.source_layer_combobox.addItem(layer.name, layer)
            if selected_name is not None:
                index = self.source_layer_combobox.findText(selected_name)
                if index >= 0:
                    self.source_layer_combobox.setCurrentIndex(index)

        self.generate_button.setEnabled(bool(points_layers))

    def _refresh_controls(self) -> None:
        overlay = self._selected_overlay
        enabled = overlay is not None
        self._set_controls_enabled(enabled)
        if overlay is None:
            return

        self._on_visible_change()
        self._on_position_change()
        self._on_source_layer_change()
        self._on_auto_sync_change()
        self._on_text_color_change()
        self._on_font_size_change()
        self._on_marker_size_change()
        self._on_padding_change()
        self._on_row_spacing_change()
        self._on_background_color_change()
        self._on_border_color_change()
        self._on_border_width_change()

    def _on_overlay_collection_change(self, _event=None) -> None:
        """Refresh overlay selection when legends are added or removed."""
        self._refresh_overlay_combo()

    def on_change_overlay(self) -> None:
        """Update controls when selected legend changes."""
        self._connect_selected_overlay(self._current_overlay())
        self._refresh_controls()

    def on_generate_from_points(self) -> None:
        """Regenerate the selected legend from the selected Points layer."""
        layer = ty.cast(Points | None, self.source_layer_combobox.currentData())
        if layer is None:
            return
        overlay_name = self._current_overlay_name() or LEGEND_OVERLAY_NAME
        overlay = self._selected_overlay
        if overlay is None:
            self.viewer.set_legend_from_points(
                layer,
                name=overlay_name,
                sync=self.auto_sync_checkbox.isChecked(),
            )
        else:
            self.viewer.set_legend_from_points(
                layer,
                name=overlay_name,
                sync=self.auto_sync_checkbox.isChecked(),
                visible=overlay.visible,
                position=overlay.position,
                text_color=overlay.text_color,
                font_size=overlay.font_size,
                marker_size=overlay.marker_size,
                row_spacing=overlay.row_spacing,
                padding=overlay.padding,
                background_color=overlay.background_color,
                border_color=overlay.border_color,
                border_width=overlay.border_width,
            )
        self._refresh_overlay_combo()

    def _on_source_layer_change(self, _event=None) -> None:
        """Update source layer selection."""
        self._refresh_source_combo()

    def on_change_auto_sync(self) -> None:
        """Update selected legend source auto-sync state."""
        overlay_name = self._current_overlay_name()
        if overlay_name is not None:
            self.viewer.set_legend_auto_sync(overlay_name, self.auto_sync_checkbox.isChecked())

    def _on_auto_sync_change(self, _event=None) -> None:
        """Update auto-sync control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.auto_sync_checkbox):
            self.auto_sync_checkbox.setChecked(overlay.sync_with_source)

    def on_change_visible(self) -> None:
        """Update selected legend visibility."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        """Update visibility control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.visible_checkbox):
            self.visible_checkbox.setChecked(overlay.visible)

    def on_change_position(self) -> None:
        """Update selected legend position."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None) -> None:
        """Update position control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.position_combobox):
            hp.set_combobox_current_index(self.position_combobox, overlay.position)

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_text_color(self, color: np.ndarray) -> None:
        """Update selected legend text color."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.text_color = color

    def _on_text_color_change(self, _event=None) -> None:
        """Update text color control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.text_color_swatch):
            self.text_color_swatch.setColor(overlay.text_color)

    def on_change_font_size(self) -> None:
        """Update selected legend font size."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None) -> None:
        """Update font size control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.font_size_spinbox):
            self.font_size_spinbox.setValue(overlay.font_size)

    def on_change_marker_size(self) -> None:
        """Update selected legend marker size."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.marker_size = self.marker_size_spinbox.value()

    def _on_marker_size_change(self, _event=None) -> None:
        """Update marker size control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.marker_size_spinbox):
            self.marker_size_spinbox.setValue(overlay.marker_size)

    def on_change_padding(self) -> None:
        """Update selected legend padding."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.padding = self.padding_spinbox.value()

    def _on_padding_change(self, _event=None) -> None:
        """Update padding control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.padding_spinbox):
            self.padding_spinbox.setValue(overlay.padding)

    def on_change_row_spacing(self) -> None:
        """Update selected legend row spacing."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.row_spacing = self.row_spacing_spinbox.value()

    def _on_row_spacing_change(self, _event=None) -> None:
        """Update row spacing control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.row_spacing_spinbox):
            self.row_spacing_spinbox.setValue(overlay.row_spacing)

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_background_color(self, color: np.ndarray) -> None:
        """Update selected legend background color."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.background_color = color

    def _on_background_color_change(self, _event=None) -> None:
        """Update background color control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.background_color_swatch):
            self.background_color_swatch.setColor(overlay.background_color)

    @Slot(np.ndarray)  # type: ignore[misc]
    def on_change_border_color(self, color: np.ndarray) -> None:
        """Update selected legend border color."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.border_color = color

    def _on_border_color_change(self, _event=None) -> None:
        """Update border color control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.border_color_swatch):
            self.border_color_swatch.setColor(overlay.border_color)

    def on_change_border_width(self) -> None:
        """Update selected legend border width."""
        overlay = self._selected_overlay
        if overlay is not None:
            overlay.border_width = self.border_width_spinbox.value()

    def _on_border_width_change(self, _event=None) -> None:
        """Update border width control."""
        overlay = self._selected_overlay
        if overlay is None:
            return
        with hp.qt_signals_blocked(self.border_width_spinbox):
            self.border_width_spinbox.setValue(overlay.border_width)

    def on_clear_selected_overlay(self) -> None:
        """Clear the selected legend overlay."""
        overlay_name = self._current_overlay_name()
        if overlay_name is not None:
            self.viewer.clear_legend(overlay_name)

    def close(self) -> None:
        """Disconnect events when widget is closing."""
        self._connect_selected_overlay(None)
        disconnect_events(self.viewer._overlays.events, self)
        disconnect_events(self.viewer.layers.events, self)
        super().close()
