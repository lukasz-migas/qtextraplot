"""Toolbar."""

from __future__ import annotations

from contextlib import suppress

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
                "none",
                tooltip="Disable data extraction (default)",
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
                    [self.tools_lasso_btn, self.tools_poly_btn, self.tools_ellipse_btn, self.tools_rectangle_btn]
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
            checked=viewer.grid.enabled,
            checked_icon_name="grid_on",
            action="napari:toggle_grid",
            func_menu=self.open_grid_popup,
        )
        toolbar_right.add_button(self.tools_grid_btn)
        if self.allow_crosshair:
            self.tools_cross_btn = toolbar_right.add_qta_tool(
                "crosshair",
                tooltip="Show/hide crosshair",
                checkable=True,
                check=self.viewer.cross_hair.visible,
                func=self._toggle_crosshair_visible,
                func_menu=self.on_open_crosshair_config,
            )
        self.tools_text_btn = toolbar_right.add_qta_tool(
            "text",
            tooltip="Show/hide text label",
            check=self.viewer.text_overlay.visible,
            func=self._toggle_text_visible,
            func_menu=self.on_open_text_config,
        )
        self.tools_scalebar_btn = toolbar_right.add_qta_tool(
            "ruler",
            tooltip="Show/hide scalebar",
            checkable=True,
            check=self.viewer.scale_bar.visible,
            func=self._toggle_scale_bar_visible,
            func_menu=self.on_open_scalebar_config,
        )
        self.tools_colorbar_btn = toolbar_right.add_qta_tool(
            "colorbar",
            tooltip="Show/hide colorbar",
            checkable=True,
            func=self._toggle_color_bar_visible,
            func_menu=self.on_open_colorbar_config,
        )
        self.tools_clip_btn = toolbar_right.add_qta_tool(
            "screenshot",
            tooltip="Copy figure to clipboard",
            func=self.on_copy_to_clipboard,
            func_menu=self.on_open_save_figure,
        )
        self.tools_save_btn = toolbar_right.add_qta_tool(
            "save",
            tooltip="Save figure",
            func=self.on_save_figure,
            func_menu=self.on_open_save_figure,
        )
        self.tools_zoomout_btn = toolbar_right.add_qta_tool(
            "zoom_out",
            tooltip="Reset view. Hold 'Control' and double-click to reset view.",
            func=viewer.reset_view,
        )
        self.tools_erase_btn = toolbar_right.add_qta_tool(
            "erase", tooltip="Clear image", func=viewer.clear_canvas, hide=True
        )
        toolbar_right.add_spacer()
        if toolbar_right.n_items <= 1:  # exclude spacer from the count
            toolbar_right.setVisible(False)

    def on_save_figure(self, path=None):
        """Export figure."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.qt_viewer.screenshot, self, history=[])
        if dialog.exec_():
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
        self.qt_viewer.viewer.scale_bar.events.visible.connect(
            lambda x: self.tools_scalebar_btn.setChecked(self.qt_viewer.viewer.scale_bar.visible)
        )

        self.qt_viewer.viewer.grid.events.enabled.connect(
            lambda x: self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid.enabled)
        )

        # try:
        #     self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        #     self.tools_grid_btn.clicked.connect(self._toggle_grid_lines_visible)
        #     self.qt_viewer.viewer.grid_lines.events.visible.connect(
        #         lambda x: self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        #     )
        # except KeyError:
        #     pass

        with suppress(KeyError):
            self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible)
            self.tools_colorbar_btn.clicked.connect(self._toggle_color_bar_visible)
            self.qt_viewer.viewer.color_bar.events.visible.connect(
                lambda x: self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible)
            )

        self.qt_viewer.viewer.text_overlay.events.visible.connect(
            lambda x: self.tools_text_btn.setChecked(self.qt_viewer.viewer.text_overlay.visible)
        )

        if self.allow_crosshair:
            self.qt_viewer.viewer.cross_hair.events.visible.connect(
                lambda x: self.tools_cross_btn.setChecked(self.qt_viewer.viewer.cross_hair.visible)
            )

    def _toggle_scale_bar_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.scale_bar.visible = state

    def _toggle_grid_lines_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_color_bar_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.color_bar.visible = state

    def _toggle_text_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.text_overlay.visible = state

    def _toggle_crosshair_visible(self, state: bool) -> None:
        self.qt_viewer.viewer.cross_hair.visible = state

    def on_open_crosshair_config(self) -> None:
        """Open text config."""
        from qtextraplot._napari.component_controls.qt_crosshair_controls import QtCrosshairControls

        dlg = QtCrosshairControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_text_config(self) -> None:
        """Open text config."""
        from qtextraplot._napari.component_controls.qt_text_overlay_controls import QtTextOverlayControls

        dlg = QtTextOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_scalebar_config(self) -> None:
        """Open scalebar config."""
        from qtextraplot._napari.component_controls.qt_scalebar_controls import QtScaleBarControls

        dlg = QtScaleBarControls(self.viewer, self.qt_viewer)
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
