"""Qt widget that embeds the canvas."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
import qtextra.helpers as hp
from napari._qt.containers import QtLayerList
from napari._qt.qt_main_window import Window, _QtMainWindow
from napari._qt.qt_viewer import QtViewer as _QtViewer
from napari._qt.widgets.qt_dims import QtDims
from napari._vispy.canvas import VispyCanvas
from napari.utils.key_bindings import KeymapHandler
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtWidgets import QWidget
from superqt import ensure_main_thread

from qtextraplot._napari._qt_viewer_utils import (
    QtViewerInstanceTracker,
    calc_status_from_cursor,
    cleanup_qt_viewer,
    copy_screenshot_to_clipboard,
    set_mouse_over_status,
    show_controls_dialog,
    toggle_controls_dialog,
)
from qtextraplot._napari._vispy import register_vispy_overlays
from qtextraplot._napari.image._qapp_model import init_qactions, reset_default_keymap
from qtextraplot._napari.image._vispy import register_vispy_overlays as register_image_vispy_overlays
from qtextraplot._napari.image.component_controls.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from qtextraplot._napari.image.component_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar

if ty.TYPE_CHECKING:
    from napari.viewer import Viewer

reset_default_keymap()
register_vispy_overlays()
register_image_vispy_overlays()


class QtViewer(QtViewerInstanceTracker, QWidget):
    """Widget view."""

    _layers_controls_dialog = None

    def __init__(
        self,
        viewer,
        parent=None,
        disable_controls: bool = False,
        add_dims: bool = True,
        add_toolbars: bool = True,
        **kwargs: ty.Any,
    ):
        # set attributes
        self._disable_controls = disable_controls

        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True)
        # Create the experimental QtPool for the monitor.
        self._qt_poll = None
        # Create the experimental RemoteManager for the monitor.
        self._remote_manager = None

        self.viewer = viewer
        self._register_instance(_QtMainWindow._instances)
        self._qt_viewer = self._qt_window = self

        self.dims = QtDims(self.viewer.dims)
        self._controls = None
        self._layers = None
        self._layersButtons = None
        self._viewerButtons = None
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._console_backlog = []
        self._console = None

        # This dictionary holds the corresponding vispy visual for each layer
        self.canvas = VispyCanvas(
            viewer=viewer,
            parent=self,
            key_map_handler=self._key_map_handler,
            size=self.viewer._canvas_size,
            autoswap=True,
        )
        self._welcome_widget = self.canvas.native  # we don't need welcome widget

        self.viewer._layer_slicer.events.ready.connect(self._on_slice_ready)

        # this is the line that initializes any Qt-based app-model Actions that
        # were defined somewhere in the `_qt` module and imported in init_qactions
        init_qactions()

        with suppress(IndexError):
            viewer.cursor.events.position.disconnect(viewer.update_status_from_cursor)
        viewer.cursor.events.position.connect(self.update_status_and_tooltip)

        self._on_active_change()
        self.viewer.layers.events.inserted.connect(self._update_camera_depth)
        self.viewer.layers.events.removed.connect(self._update_camera_depth)
        self.viewer.dims.events.ndisplay.connect(self._update_camera_depth)
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)
        self.viewer.events.zoom.connect(self._on_update_zoom)

        # bind shortcuts stored in settings last.
        _QtViewer._bind_shortcuts(self)

        for layer in self.viewer.layers:
            self._add_layer(layer)

        self._set_layout(add_dims=add_dims, add_toolbars=add_toolbars, **kwargs)

    def _set_layout(self, add_dims: bool, add_toolbars: bool, **kwargs):
        # set in main canvas
        self.viewerToolbar = QtViewToolbar(view=self.view, viewer=self.viewer, qt_viewer=self, **kwargs)

        # layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self, self.viewer)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self, self.viewer, **kwargs)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self, self.viewer, **kwargs)

        image_layout = hp.make_v_layout(margin=(0, 2, 0, 2) if add_dims else (0, 0, 0, 0), spacing=0)
        image_layout.addWidget(self.canvas.native, stretch=True)
        if add_dims:
            image_layout.addWidget(self.dims)

        # view widget
        main_layout = hp.make_h_layout(spacing=1 if add_toolbars else 0, margin=2, parent=self)
        main_layout.addLayout(image_layout, stretch=True)
        if add_toolbars:
            main_layout.insertWidget(0, self.viewerToolbar.toolbar_left)
            main_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_left.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)

    @property
    def view(self):
        return self.canvas.view

    @ensure_main_thread
    def _on_slice_ready(self, event):
        _QtViewer._on_slice_ready(self, event)

    def update_status_and_tooltip(self) -> None:
        """Set statusbar."""
        with suppress(Exception):
            status_and_tooltip = calc_status_from_cursor(self.viewer)
            _QtMainWindow.set_status_and_tooltip(self, status_and_tooltip)

    def _update_camera_depth(self):
        _QtViewer._update_camera_depth(self)

    def _on_active_change(self):
        _QtViewer._on_active_change(self)

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
        copy_screenshot_to_clipboard(
            self._screenshot,
            flash=flash,
            canvas_only=canvas_only,
            size=size,
            scale=scale,
            fit_to_data_extent=fit_to_data_extent,
        )

    def on_save_figure(
        self,
        size: tuple[int, int] | None = None,
        scale: float | None = None,
        flash: bool = True,
        canvas_only: bool = False,
    ) -> None:
        """Save figure."""
        from qtextra.helpers import get_save_filename

        path = get_save_filename(self, file_filter="Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if path:
            self.screenshot(
                path=path,
                size=size,
                scale=scale,
                canvas_only=canvas_only,
                flash=flash,
            )

    def _on_add_layer_change(self, event):
        _QtViewer._on_add_layer_change(self, event)

    def _add_layer(self, layer):
        _QtViewer._add_layer(self, layer)

    def _on_update_zoom(self, event):
        """Update zoom level."""
        from qtextraplot._napari.image.utilities import calculate_zoom

        xmin, xmax, ymin, ymax = event.value
        zoom, ycenter, xcenter = calculate_zoom(xmin, xmax, ymin, ymax, self.viewer)
        self.viewer.camera.center = (1, ycenter, xcenter)
        # calculate zoom by checking the current extents
        self.viewer.camera.zoom = zoom

    def on_open_controls_dialog(self, event=None) -> None:
        """Open dialog responsible for layer settings."""
        from qtextraplot._napari.image.component_controls.qt_layers_dialog import DialogNapariControls

        show_controls_dialog(self, DialogNapariControls)

    def on_toggle_controls_dialog(self, _event=None) -> None:
        """Toggle between on/off state of the layer settings."""
        toggle_controls_dialog(self, self.on_open_controls_dialog)

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        # if the viewer.QtDims object is playing an axis, we need to terminate
        # the AnimationThread before close, otherwise it will cause a segFault
        # or Abort trap. (calling stop() when no animation is occurring is also
        # not a problem)
        cleanup_qt_viewer(event, dims=self.dims, canvas_native=self.canvas.native)

    def enterEvent(self, event: QEvent) -> None:
        """Emit our own event when mouse enters the canvas."""
        set_mouse_over_status(self.viewer, True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Emit our own event when mouse leaves the canvas."""
        set_mouse_over_status(self.viewer, False)
        super().leaveEvent(event)
