"""Qt widget that embeds the canvas."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
import qtextra.helpers as hp
from napari._qt.containers.qt_layer_list import QtLayerList
from napari._qt.widgets.qt_dims import QtDims
from napari.utils.key_bindings import KeymapHandler
from napari_plot._qt._qapp_model import init_qactions, reset_default_keymap
from napari_plot._qt.qt_main_window import Window, _QtMainWindow
from napari_plot._qt.qt_viewer import QtViewer as _QtViewer
from napari_plot._vispy.overlays import register_vispy_overlays
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextraplot._napari.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextraplot._napari.line._vispy.canvas import VispyCanvas
from qtextraplot._napari.line.component_controls.qt_view_toolbar import QtViewLeftToolbar, QtViewRightToolbar
from qtextraplot._napari.line.layer_controls.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from qtextraplot.config import CANVAS, CanvasThemes

if ty.TYPE_CHECKING:
    from napari_plot.viewer import Viewer

reset_default_keymap()
register_vispy_overlays()


def _calc_status_from_cursor(viewer: Viewer) -> tuple[str | dict, str]:
    if not viewer.mouse_over_canvas:
        return None
    active = viewer.layers.selection.active
    if active is not None and active._loaded:
        status = active.get_status(
            viewer.cursor.position,
            view_direction=viewer.cursor._view_direction,
            dims_displayed=list(viewer.dims.displayed),
            world=True,
        )
        tooltip_text = ""
        if viewer.tooltip.visible:
            tooltip_text = active._get_tooltip_text(
                np.asarray(viewer.cursor.position),
                view_direction=np.asarray(viewer.cursor._view_direction),
                dims_displayed=list(viewer.dims.displayed),
                world=True,
            )
        return status, tooltip_text
    x, y = viewer.cursor.position
    status = f"[{round(x)} {round(y)}]"
    return status, status


def as_array(name: str, canvas: CanvasThemes) -> np.ndarray:
    """Return color array."""
    from napari.utils.colormaps.standardize_color import transform_color

    color = getattr(canvas.active, name)
    return transform_color(color.as_hex())[0]


class QtViewer(QWidget):
    """Qt view for the napari Viewer model."""

    # To track window instances and facilitate getting the "active" viewer...
    # We use this instead of QApplication.activeWindow for compatibility with
    # IPython usage. When you activate IPython, it will appear that there are
    # *no* active windows, so we want to track the most recently active windows
    _instances: ty.ClassVar[list[QWidget]] = []
    _instance_index: ty.ClassVar[int] = -1

    _layers_controls_dialog = None

    def __init__(
        self,
        viewer: Viewer,
        parent=None,
        disable_controls: bool = False,
        add_toolbars: bool = True,
        allow_extraction: bool = True,
        allow_tools: bool = False,
        connect_theme: bool = True,
        **kwargs: ty.Any,
    ):
        self._disable_controls = disable_controls

        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True)

        self.viewer = viewer
        self._instances.append(self)
        # essential that these are set because we need to use the providers for in_and_out
        _QtMainWindow._instances.append(self)
        _QtViewer._instances.append(self)
        self._qt_viewer = self._qt_window = self
        self.current_index = len(self._instances) - 1

        self.dims = QtDims(self.viewer.dims)
        self._controls = None
        self._layers = None
        self._layersButtons = None
        self._viewerButtons = None
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._console_backlog = []
        self._console = None

        self.canvas = VispyCanvas(
            viewer=self.viewer,
            parent=self,
            key_map_handler=self._key_map_handler,
            size=self.viewer._canvas_size,
            autoswap=True,
        )
        self._welcome_widget = self.canvas.native  # we don't need welcome widget

        # this is the line that initializes any Qt-based app-model Actions that
        # were defined somewhere in the `_qt` module and imported in init_qactions
        init_qactions()

        with suppress(IndexError):
            viewer.cursor.events.position.disconnect(viewer.update_status_from_cursor)
        viewer.cursor.events.position.connect(self.update_status_and_tooltip)

        self._on_active_change()
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)
        # self.viewer.events.zoom.connect(self._on_update_zoom)
        # self.viewer.layers.events.removed.connect(self._remove_layer)

        # bind shortcuts stored in settings last.
        _QtViewer._bind_shortcuts(self)

        for layer in self.viewer.layers:
            self._add_layer(layer)

        self._set_layout(
            add_toolbars=add_toolbars, allow_extraction=allow_extraction, allow_tools=allow_tools, **kwargs
        )

        self.viewer_left_toolbar.connect_toolbar()
        self.viewer_right_toolbar.connect_toolbar()

        if connect_theme:
            CANVAS.evt_theme_changed.connect(self.toggle_theme)
            self.toggle_theme()  # force theme change

    def _set_layout(self, add_toolbars: bool, **kwargs):
        # set in main canvas
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self, self.viewer)
        # widget showing current layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewer_left_toolbar = QtViewLeftToolbar(self.canvas.view, self.viewer, self, **kwargs)
        self.viewer_right_toolbar = QtViewRightToolbar(self.canvas.view, self.viewer, self, **kwargs)

        image_layout = hp.make_v_layout(margin=(0, 2, 0, 2))
        image_layout.addWidget(self.canvas.native, stretch=True)

        # view widget
        main_layout = hp.make_h_layout(spacing=1 if add_toolbars else 0, margin=2, parent=self)
        main_layout.addLayout(image_layout, stretch=True)
        if add_toolbars:
            main_layout.insertWidget(0, self.viewer_left_toolbar)
            main_layout.addWidget(self.viewer_right_toolbar)
        else:
            self.viewer_left_toolbar.setVisible(False)
            self.viewer_right_toolbar.setVisible(False)

    def _on_active_change(self):
        _QtViewer._on_active_change(self)

    def _on_add_layer_change(self, event):
        _QtViewer._on_add_layer_change(self, event)

    def _add_layer(self, layer):
        _QtViewer._add_layer(self, layer)

    def update_status_and_tooltip(self) -> None:
        """Set statusbar."""
        with suppress(Exception):
            status_and_tooltip = _calc_status_from_cursor(self.viewer)
            _QtMainWindow.set_status_and_tooltip(self, status_and_tooltip)

    def toggle_theme(self, _=None):
        """Update theme."""
        self.canvas.bgcolor = as_array("canvas", CANVAS)
        self.viewer.axis.label_color = as_array("axis", CANVAS)
        self.viewer.axis.tick_color = as_array("axis", CANVAS)
        self.viewer.text_overlay.color = as_array("label", CANVAS)

    @property
    def x_axis(self):
        """Return x-axis."""
        return self.canvas.x_axis

    @property
    def y_axis(self):
        """Return y-axis."""
        return self.canvas.y_axis

    @property
    def text_overlay(self):
        """Return text overlay."""
        return self.canvas._overlay_to_visual[self.viewer.text_overlay]

    @property
    def layer_to_visual(self):
        """Mapping of Napari layer to Vispy layer. Added for backward compatibility"""
        return self.canvas.layer_to_visual

    def on_resize(self, event):
        """Update cached x-axis offset."""
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

    def _on_boxzoom(self, event):
        """Update boxzoom visibility."""
        self.viewer.span.visible = event.visible
        if not event.visible:
            self.viewer.span.position = 0, 0
        # self.viewer.boxzoom.visible = event.visible
        # if not event.visible:  # reset so next time its displayed it will be not visible to the user
        #     self.viewer.boxzoom.rect = 0, 0, 0, 0

    def _on_boxzoom_move(self, event):
        """Update boxzoom."""
        rect = event.rect
        self.viewer.span.position = rect[0], rect[1]

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings."""
        from qtextraplot._napari.line.component_controls.qt_layers_dialog import DialogLineControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = DialogLineControls(self)
        # make sure the dialog is shown
        self._layers_controls_dialog.show()
        # make sure the the dialog gets focus
        self._layers_controls_dialog.raise_()  # for macOS
        self._layers_controls_dialog.activateWindow()  # for Windows

    def on_save_figure(self, path=None):
        """Export figure."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self, history=[])
        if dialog.exec_():
            pass

    def screenshot(self, path=None, size=None, scale=None, flash=True, canvas_only=False) -> np.ndarray:
        """Capture a screenshot of the Vispy canvas."""
        return Window.screenshot(self, path=path, flash=flash, size=size, scale=scale, canvas_only=canvas_only)

    def _screenshot(
        self,
        size: tuple[int, int] | None = None,
        scale: float | None = None,
        flash: bool = True,
        canvas_only: bool = False,
        fit_to_data_extent: bool = False,
    ):
        """Capture a screenshot of the Vispy canvas."""
        return Window._screenshot(
            self, size=size, scale=scale, flash=flash, canvas_only=canvas_only, fit_to_data_extent=fit_to_data_extent
        )

    def clipboard(
        self,
        size: tuple[int, int] | None = None,
        scale: float | None = None,
        flash: bool = True,
        canvas_only: bool = False,
        fit_to_data_extent: bool = False,
    ):
        """Take a screenshot of the currently displayed screen and copy the image to the clipboard."""
        img = self._screenshot(
            flash=flash, canvas_only=canvas_only, size=size, scale=scale, fit_to_data_extent=fit_to_data_extent
        )
        QApplication.clipboard().setImage(img)

    def on_toggle_controls_dialog(self, _event=None) -> None:
        """Toggle between on/off state of the layer settings."""
        if self._disable_controls:
            return
        if self._layers_controls_dialog is None:
            self.on_open_controls_dialog()
        else:
            self._layers_controls_dialog.setVisible(not self._layers_controls_dialog.isVisible())

    def enterEvent(self, event: QEvent) -> None:
        """Emit our own event when mouse enters the canvas."""
        self.viewer.status = "Ready"
        self.viewer.mouse_over_canvas = True
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Emit our own event when mouse leaves the canvas."""
        self.viewer.status = ""
        self.viewer.mouse_over_canvas = False
        super().leaveEvent(event)

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        CANVAS.evt_theme_changed.disconnect(self.toggle_theme)
        self.canvas.native.deleteLater()
        event.accept()

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        if hasattr(event, "native"):
            event = event.native
        self.canvas._scene_canvas._backend._keyEvent(self.canvas._scene_canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        if hasattr(event, "native"):
            event = event.native
        self.canvas._scene_canvas._backend._keyEvent(self.canvas._scene_canvas.events.key_release, event)
        event.accept()
