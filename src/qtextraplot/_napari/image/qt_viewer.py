"""Qt widget that embeds the canvas."""

import typing as ty
from weakref import WeakSet

from napari._qt._qapp_model.qactions import add_dummy_actions, init_qactions
from napari._qt.containers import QtLayerList
from napari._qt.qt_main_window import _QtMainWindow
from napari._qt.qt_viewer import QtViewer as _QtViewer
from napari._qt.qt_viewer import _create_qt_poll, _create_remote_manager
from napari._qt.widgets.qt_dims import QtDims
from napari._vispy.canvas import VispyCanvas
from napari.utils.key_bindings import KeymapHandler
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from superqt import ensure_main_thread

from qtextraplot._napari.common._vispy.overlays import register_vispy_overlays
from qtextraplot._napari.common.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextraplot._napari.image.component_controls.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from qtextraplot._napari.image.component_controls.qt_view_toolbar import QtViewToolbar

register_vispy_overlays()


class QtViewer(QWidget):
    """Widget view."""

    _instances = WeakSet()

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
        self.viewer = viewer

        self._instances.add(self)
        _QtMainWindow._instances.append(self)
        self._qt_viewer = self
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True)

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

        self.viewer._layer_slicer.events.ready.connect(self._on_slice_ready)

        # this is the line that initializes any Qt-based app-model Actions that
        # were defined somewhere in the `_qt` module and imported in init_qactions
        init_qactions()

        # TODO: the dummy actions should **not** live on the layerlist context
        # as they are unrelated. However, we do not currently have a suitable
        # enclosing context where we could store these keys, such that they
        # **and** the layerlist context key are available when we update
        # menus. We need a single context to contain all keys required for
        # menu update, so we add them to the layerlist context for now.
        add_dummy_actions(self.viewer.layers._ctx)

        self._on_active_change()
        self.viewer.layers.events.inserted.connect(self._update_camera_depth)
        self.viewer.layers.events.removed.connect(self._update_camera_depth)
        self.viewer.dims.events.ndisplay.connect(self._update_camera_depth)
        self.viewer.layers.selection.events.active.connect(self._on_active_change)

        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)

        self.setAcceptDrops(True)

        # Create the experimental QtPool for the monitor.
        self._qt_poll = _create_qt_poll(self, self.viewer.camera)

        # Create the experimental RemoteManager for the monitor.
        self._remote_manager = _create_remote_manager(self.viewer.layers, self._qt_poll)

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
        self.controls = QtLayerControlsContainer(self.viewer)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer, **kwargs)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewerToolbar = QtViewToolbar(self.view, self.viewer, self, **kwargs)

        image_layout = QVBoxLayout()
        image_layout.addWidget(self.canvas.native, stretch=True)
        image_layout.setContentsMargins(0, 2, 0, 2)
        if add_dims:
            image_layout.addWidget(self.dims)
            image_layout.setSpacing(0)
        else:
            image_layout.setSpacing(0)
            image_layout.setContentsMargins(0, 0, 0, 0)

        # view widget
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(1)
        main_layout.addLayout(image_layout)
        main_layout.setContentsMargins(2, 2, 2, 2)
        if add_toolbars:
            main_layout.insertWidget(0, self.viewerToolbar.toolbar_left)
            main_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_left.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)
            main_layout.setSpacing(0)

    @property
    def view(self):
        return self.canvas.view

    @ensure_main_thread
    def _on_slice_ready(self, event):
        _QtViewer._on_slice_ready(self, event)

    def _update_camera_depth(self):
        _QtViewer._update_camera_depth(self)

    def _on_active_change(self):
        _QtViewer._on_active_change(self)

    def _on_add_layer_change(self, event):
        _QtViewer._on_add_layer_change(self, event)

    def _add_layer(self, layer):
        _QtViewer._add_layer(self, layer)

    def on_open_controls_dialog(self, event=None) -> None:
        """Open dialog responsible for layer settings."""
        from qtextraplot._napari.image.component_controls.qt_layers_dialog import DialogNapariControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = DialogNapariControls(self)
        # make sure the dialog is shown
        self._layers_controls_dialog.show()
        # make sure the dialog gets focus
        self._layers_controls_dialog.raise_()  # for macOS
        self._layers_controls_dialog.activateWindow()  # for Windows

    def on_toggle_controls_dialog(self, _event=None) -> None:
        """Toggle between on/off state of the layer settings."""
        if self._disable_controls:
            return
        if self._layers_controls_dialog is None:
            self.on_open_controls_dialog()
        else:
            self._layers_controls_dialog.setVisible(not self._layers_controls_dialog.isVisible())

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
        self.dims.stop()
        self.canvas.native.deleteLater()
        event.accept()
