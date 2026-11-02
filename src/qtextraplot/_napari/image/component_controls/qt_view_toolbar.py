"""Toolbar."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import qtextra.helpers as hp
from napari.utils.events.event import EmitterGroup, Event
from qtextra.helpers import make_radio_btn_group
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QWidget

from qtextraplot._napari.image.component_controls.qt_layer_buttons import make_qta_btn


class QtViewToolbar(QWidget):
    """Qt toolbars."""

    # layers
    _reg_image_layer = None

    _dlg_labels: QDialog | None = None
    _dlg_shapes: QDialog | None = None

    # @property
    # def view_image(self) -> NapariImageView:
    #     """Napari image view."""
    #     return self.qt_viewer

    def __init__(self, view, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer)
        self.view = view
        self.viewer = viewer
        self.qt_viewer = qt_viewer

        # user kwargs
        self.allow_extraction = kwargs.pop("allow_extraction", True)
        self.allow_shapes = kwargs.pop("allow_shapes", True)
        self.allow_masks = kwargs.pop("allow_masks", False)
        self.allow_labels = kwargs.pop("allow_labels", False)
        self.allow_crosshair = kwargs.pop("allow_crosshair", True)
        self.allow_object_outlines = kwargs.pop("allow_object_outlines", True)
        self.allow_legend = kwargs.pop("allow_legend", True)
        self._connected_object_outline_overlays = []
        self._connected_legend_overlays = []
        self._connected_name_overlays: list[ty.Any] = []

        self.events = EmitterGroup(
            auto_connect=False,
            # shapes
            shapes_open=Event,
            shapes_extract=Event,
            shapes_cancel=Event,
            # labels
            labels_open=Event,
            labels_extract=Event,
            labels_cancel=Event,
            # general
            crosshair=Event,
            selection_off=Event,
            # masks
            mask_extract=Event,
        )

        # create instance
        self.toolbar_left = toolbar_left = QtMiniToolbar(qt_viewer, Qt.Orientation.Vertical, add_spacer=False)
        self.toolbar_right = toolbar_right = QtMiniToolbar(qt_viewer, Qt.Orientation.Vertical, add_spacer=False)

        # left-side toolbar
        # this branch provides additional tools in the toolbar to allow extraction
        if self.allow_extraction:
            self.tools_off_btn = toolbar_left.add_qta_tool(
                "zoom",
                tooltip="Click here to enable default zoom interaction",
                checkable=True,
                check=True,
            )
            buttons = [self.tools_off_btn]
            if self.allow_shapes:
                self.tools_rectangle_btn = toolbar_left.add_qta_tool(
                    "rectangle",
                    tooltip="Use rectangular region of interest",
                    checkable=True,
                )
                self.tools_ellipse_btn = toolbar_left.add_qta_tool(
                    "ellipse",
                    tooltip="Use circular region of interest",
                    checkable=True,
                )
                self.tools_poly_btn = toolbar_left.add_qta_tool(
                    "polygon",
                    tooltip="Use polygon region of interest",
                    checkable=True,
                )
                self.tools_lasso_btn = toolbar_left.add_qta_tool(
                    "lasso",
                    tooltip="Use lasso region of interest",
                    checkable=True,
                )
                buttons.extend(
                    [self.tools_lasso_btn, self.tools_poly_btn, self.tools_ellipse_btn, self.tools_rectangle_btn],
                )
            if self.allow_labels:
                self.tools_new_labels_btn = toolbar_left.add_qta_tool(
                    "new_labels",
                    tooltip="Paint region of interest using paint brush",
                    checkable=True,
                )
                buttons.append(self.tools_new_labels_btn)
            _radio_group = make_radio_btn_group(qt_viewer, buttons)
            toolbar_left.add_spacer()
        if toolbar_left.n_items <= 1:  # exclude spacer from the count
            toolbar_left.setVisible(False)

        # right-hand toolbar
        self.layers_btn = toolbar_right.add_qta_tool(
            "layers",
            tooltip="Display layer controls",
            checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )
        self.tools_grid_btn = make_qta_btn(
            self,
            "grid_off",
            "Toggle grid view. Right-click on the button to change grid settings.",
            checkable=True,
            checked=self.viewer.canvas.grid.enabled,
            checked_icon_name="grid_on",
            func=self._toggle_grid_visible,
            func_menu=self.open_grid_popup,
        )
        toolbar_right.add_button(self.tools_grid_btn)
        if self.allow_crosshair:
            self.tools_cross_btn = toolbar_right.add_qta_tool(
                "crosshair",
                tooltip="Show/hide crosshair. Right-click on the button to change crosshair settings.",
                checkable=True,
                check=self.viewer.cross_hair.visible,
                func=self._toggle_crosshair_visible,
                func_menu=self.on_open_crosshair_config,
            )
        if self.allow_object_outlines:
            self.tools_object_outlines_btn = toolbar_right.add_qta_tool(
                "polygon",
                tooltip="Show/hide object outlines. Right-click on the button to change object outline settings.",
                checkable=True,
                check=self.viewer.object_outlines_visible,
                func=self._toggle_object_outlines_visible,
                func_menu=self.on_open_object_outline_config,
            )
            self.viewer.scene.overlays.events.added.connect(self._refresh_object_outline_event_connections)
            self.viewer.scene.overlays.events.removed.connect(self._refresh_object_outline_event_connections)
            self.viewer.scene.overlays.events.changed.connect(self._refresh_object_outline_event_connections)
            self._refresh_object_outline_event_connections()
        if self.allow_legend:
            self.tools_legend_btn = toolbar_right.add_qta_tool(
                "legend",
                tooltip="Show/hide legend. Right-click on the button to change legend settings.",
                checkable=True,
                check=self.viewer.legend_visible,
                func=self._toggle_legend_visible,
                func_menu=self.on_open_legend_config,
            )
            self.viewer.canvas.overlays.events.added.connect(self._refresh_legend_event_connections)
            self.viewer.canvas.overlays.events.removed.connect(self._refresh_legend_event_connections)
            self.viewer.canvas.overlays.events.changed.connect(self._refresh_legend_event_connections)
            self._refresh_legend_event_connections()
        self.tools_text_btn = toolbar_right.add_qta_tool(
            "text",
            tooltip="Show/hide text label. Right-click on the button to change text settings.",
            checkable=True,
            check=self.viewer.canvas.overlays.text.visible,
            func=self._toggle_text_visible,
            func_menu=self.on_open_text_config,
        )
        self.tools_name_overlay_btn = toolbar_right.add_qta_tool(
            "name_overlay",
            tooltip="Show/hide layer labels. Right-click on the button to change layer label settings.",
            checkable=True,
            check=self._all_layer_names_visible(),
            func=self._toggle_layer_names_visible,
            func_menu=self.on_open_layer_names_config,
        )
        self.viewer.layers.events.inserted.connect(self._refresh_name_overlay_event_connections)
        self.viewer.layers.events.removed.connect(self._refresh_name_overlay_event_connections)
        self.viewer.layers.events.changed.connect(self._refresh_name_overlay_event_connections)
        self._refresh_name_overlay_event_connections()
        self.tools_scalebar_btn = toolbar_right.add_qta_tool(
            "ruler",
            tooltip="Show/hide scalebar",
            checkable=True,
            check=self.viewer.canvas.overlays.scale_bar.visible,
            func=self._toggle_scale_bar_visible,
            func_menu=self.on_open_scalebar_config,
        )
        self.tools_axes_btn = toolbar_right.add_qta_tool(
            "axes",
            tooltip="Show/hide axes. Right-click on the button to change axes settings.",
            checkable=True,
            check=self._axes_visible(),
            func=self._toggle_axes_visible,
            func_menu=self.on_open_axes_config,
        )
        self.tools_cursor_crosshair_btn = toolbar_right.add_qta_tool(
            "cursor_crosshair",
            tooltip="Show/hide cursor crosshair. Right-click on the button to change cursor crosshair settings.",
            checkable=True,
            check=self.viewer.scene.overlays.crosshair.visible,
            func=self._toggle_cursor_crosshair_visible,
            func_menu=self.on_open_cursor_crosshair_config,
        )
        self.tools_coordinate_grid_btn = toolbar_right.add_qta_tool(
            "coordinate_grid",
            tooltip="Show/hide coordinate grid. Right-click on the button to change coordinate grid settings.",
            checkable=True,
            check=self.viewer.scene.overlays.coordinate_grid.visible,
            func=self._toggle_coordinate_grid_visible,
            func_menu=self.on_open_coordinate_grid_config,
        )
        self.tools_colorbar_btn = toolbar_right.add_qta_tool(
            "colorbar",
            tooltip="Show/hide colorbar. Right-click on the button to change colorbar settings.",
            checkable=True,
            func=self._toggle_color_bar_visible,
            func_menu=self.on_open_colorbar_config,
        )
        self.tools_clip_btn = toolbar_right.add_qta_tool(
            "screenshot",
            tooltip="Copy figure to clipboard. Right-click on the button to open export settings.",
            func=self.on_copy_to_clipboard,
            func_menu=self.on_open_save_figure,
        )
        self.tools_save_btn = toolbar_right.add_qta_tool(
            "save",
            tooltip="Save figure. Right-click on the button to open export settings.",
            func=self.on_save_figure,
            func_menu=self.on_open_save_figure,
        )
        self.tools_zoomout_btn = toolbar_right.add_qta_tool(
            "zoom_out",
            tooltip="Reset view. Hold 'Control' and double-click to reset view.",
            func=self.viewer.reset_view,
        )
        self.tools_erase_btn = toolbar_right.add_qta_tool(
            "erase",
            tooltip="Clear image",
            func=self.viewer.clear_canvas,
            hide=True,
        )
        toolbar_right.add_spacer()
        if toolbar_right.n_items <= 1:  # exclude spacer from the count
            toolbar_right.setVisible(False)

    def on_save_figure(self, path=None):
        """Export figure."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.qt_viewer.screenshot, self, history=[])
        if dialog.exec():
            pass

    def on_copy_to_clipboard(self):
        """Copy figure to clipboard."""
        self.qt_viewer.clipboard()

    def open_grid_popup(self) -> None:
        """Open grid options pop up widget."""
        from qtextraplot._napari.component_controls.qt_grid_controls import QtGridControls

        dlg = QtGridControls(self.viewer, self)
        dlg.show_left_of_widget(self.tools_grid_btn)

    def connect_toolbar(self) -> None:
        """Connect events."""
        self.qt_viewer.viewer.canvas.overlays.scale_bar.events.visible.connect(
            lambda x: self.tools_scalebar_btn.setChecked(self.qt_viewer.viewer.canvas.overlays.scale_bar.visible),
        )

        self.qt_viewer.viewer.canvas.grid.events.enabled.connect(
            lambda x: self.tools_grid_btn.setChecked(self.qt_viewer.viewer.canvas.grid.enabled),
        )

        with suppress(KeyError):
            self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible)
            self.tools_colorbar_btn.clicked.connect(self._toggle_color_bar_visible)
            self.qt_viewer.viewer.color_bar.events.visible.connect(
                lambda x: self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible),
            )

        self.qt_viewer.viewer.canvas.overlays.text.events.visible.connect(
            lambda x: self.tools_text_btn.setChecked(self.qt_viewer.viewer.canvas.overlays.text.visible),
        )

        self.qt_viewer.viewer.scene.overlays.axes.events.visible.connect(self._sync_axes_button)
        self.qt_viewer.viewer.canvas.overlays.axes.events.visible.connect(self._sync_axes_button)
        self.qt_viewer.viewer.scene.overlays.crosshair.events.visible.connect(
            lambda x: self.tools_cursor_crosshair_btn.setChecked(
                self.qt_viewer.viewer.scene.overlays.crosshair.visible,
            ),
        )
        self.qt_viewer.viewer.scene.overlays.coordinate_grid.events.visible.connect(
            lambda x: self.tools_coordinate_grid_btn.setChecked(
                self.qt_viewer.viewer.scene.overlays.coordinate_grid.visible,
            ),
        )

        if self.allow_crosshair:
            self.qt_viewer.viewer.cross_hair.events.visible.connect(
                lambda x: self.tools_cross_btn.setChecked(self.qt_viewer.viewer.cross_hair.visible),
            )
        if self.allow_object_outlines:
            self._refresh_object_outline_event_connections()
        if self.allow_legend:
            self._refresh_legend_event_connections()
        self._refresh_name_overlay_event_connections()

    def _toggle_grid_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.canvas.grid.enabled = state

    def _toggle_scale_bar_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.canvas.overlays.scale_bar.visible = state

    def _toggle_grid_lines_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_color_bar_visible(self, state: bool) -> None:
        for layer in self.viewer.layers:
            if hasattr(layer, "colorbar") and hasattr(layer, "rgb") and not layer.rgb:
                layer.colorbar.visible = state

    def _toggle_layer_names_visible(self, state: bool) -> None:
        for layer in self.viewer.layers:
            if hasattr(layer, "name_overlay"):
                layer.name_overlay.visible = state
        self._sync_name_overlay_button()

    def _axes_visible(self) -> bool:
        return self.viewer.scene.overlays.axes.visible or self.viewer.canvas.overlays.axes.visible

    def _toggle_axes_visible(self, state: bool) -> None:
        # the button only toggles the scene axes; when hiding, hide the canvas axes too
        self.qt_viewer.viewer.scene.overlays.axes.visible = state
        if not state:
            self.qt_viewer.viewer.canvas.overlays.axes.visible = False

    def _sync_axes_button(self, _event=None) -> None:
        with hp.qt_signals_blocked(self.tools_axes_btn):
            self.tools_axes_btn.setChecked(self._axes_visible())

    def _toggle_cursor_crosshair_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.scene.overlays.crosshair.visible = state

    def _toggle_coordinate_grid_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.scene.overlays.coordinate_grid.visible = state

    def _toggle_text_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.canvas.overlays.text.visible = state

    def _toggle_crosshair_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.cross_hair.visible = state

    def _toggle_object_outlines_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.set_object_outlines_visible(state)
        self._sync_object_outlines_button()

    def _toggle_legend_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.set_legend_visible(state)
        self._sync_legend_button()

    def _sync_object_outlines_button(self, _event=None) -> None:
        if not self.allow_object_outlines:
            return
        with hp.qt_signals_blocked(self.tools_object_outlines_btn):
            self.tools_object_outlines_btn.setChecked(self.qt_viewer.viewer.object_outlines_visible)

    def _sync_legend_button(self, _event=None) -> None:
        if not self.allow_legend:
            return
        with hp.qt_signals_blocked(self.tools_legend_btn):
            self.tools_legend_btn.setChecked(self.qt_viewer.viewer.legend_visible)

    def _all_layer_names_visible(self) -> bool:
        """Return whether every available layer name overlay is visible."""
        overlays = [layer.name_overlay for layer in self.viewer.layers if hasattr(layer, "name_overlay")]
        return bool(overlays) and all(overlay.visible for overlay in overlays)

    def _sync_name_overlay_button(self, _event: ty.Any = None) -> None:
        """Synchronize the layer name overlay toolbar button."""
        with hp.qt_signals_blocked(self.tools_name_overlay_btn):
            self.tools_name_overlay_btn.setChecked(self._all_layer_names_visible())

    def _refresh_name_overlay_event_connections(self, _event: ty.Any = None) -> None:
        """Refresh layer name overlay visibility event connections."""
        for overlay in self._connected_name_overlays:
            with suppress(TypeError, ValueError):
                overlay.events.visible.disconnect(self._sync_name_overlay_button)
        self._connected_name_overlays = [
            layer.name_overlay for layer in self.viewer.layers if hasattr(layer, "name_overlay")
        ]
        for overlay in self._connected_name_overlays:
            overlay.events.visible.connect(self._sync_name_overlay_button)
        self._sync_name_overlay_button()

    def _refresh_object_outline_event_connections(self, _event=None) -> None:
        if not self.allow_object_outlines:
            return
        for overlay in self._connected_object_outline_overlays:
            overlay.events.visible.disconnect(self._sync_object_outlines_button)
        self._connected_object_outline_overlays = list(self.qt_viewer.viewer.object_outline_overlays().values())
        for overlay in self._connected_object_outline_overlays:
            overlay.events.visible.connect(self._sync_object_outlines_button)
        self._sync_object_outlines_button()

    def _refresh_legend_event_connections(self, _event=None) -> None:
        if not self.allow_legend:
            return
        for overlay in self._connected_legend_overlays:
            overlay.events.visible.disconnect(self._sync_legend_button)
        self._connected_legend_overlays = list(self.qt_viewer.viewer.legend_overlays().values())
        for overlay in self._connected_legend_overlays:
            overlay.events.visible.connect(self._sync_legend_button)
        self._sync_legend_button()

    def on_open_crosshair_config(self) -> None:
        """Open text config."""
        from qtextraplot._napari.component_controls.qt_crosshair_controls import QtCrosshairControls

        dlg = QtCrosshairControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_object_outline_config(self) -> None:
        """Open object outline config."""
        from qtextraplot._napari.component_controls.qt_object_outline_controls import QtObjectOutlineControls

        dlg = QtObjectOutlineControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_legend_config(self) -> None:
        """Open legend config."""
        from qtextraplot._napari.component_controls.qt_legend_controls import QtLegendControls

        dlg = QtLegendControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_text_config(self) -> None:
        """Open text config."""
        from qtextraplot._napari.component_controls.qt_text_overlay_controls import QtTextOverlayControls

        dlg = QtTextOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_layer_names_config(self) -> None:
        """Open layer name overlay configuration."""
        from qtextraplot._napari.component_controls.qt_layer_name_overlay_controls import (
            QtLayerNameOverlayControls,
        )

        dlg = QtLayerNameOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_scalebar_config(self) -> None:
        """Open scalebar config."""
        from qtextraplot._napari.component_controls.qt_scalebar_controls import QtScaleBarControls

        dlg = QtScaleBarControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_axes_config(self) -> None:
        """Open axes config."""
        from qtextraplot._napari.component_controls.qt_axes_controls import QtAxesControls

        dlg = QtAxesControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_cursor_crosshair_config(self) -> None:
        """Open cursor crosshair config."""
        from qtextraplot._napari.component_controls.qt_cursor_crosshair_controls import QtCursorCrosshairControls

        dlg = QtCursorCrosshairControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_coordinate_grid_config(self) -> None:
        """Open coordinate grid config."""
        from qtextraplot._napari.component_controls.qt_coordinate_grid_controls import QtCoordinateGridControls

        dlg = QtCoordinateGridControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_colorbar_config(self) -> None:
        """Open colorbar config."""
        from qtextraplot._napari.component_controls.qt_colorbar_controls import QtColorBarControls

        dlg = QtColorBarControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_save_figure(self) -> None:
        """Show scale bar controls for the viewer."""
        from qtextraplot._napari.widgets import QtScreenshotDialog

        dlg = QtScreenshotDialog(self.qt_viewer, self)
        dlg.show_above_widget(self.tools_save_btn)
