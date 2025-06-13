"""Qt widget that embeds the canvas."""

from typing import Tuple
from weakref import WeakSet

from napari._qt.utils import QImg2array
from napari.components.overlays import CanvasOverlay, Overlay, SceneOverlay
from napari.utils.key_bindings import KeymapHandler
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QGuiApplication, QImage
from qtpy.QtWidgets import QWidget

from qtextraplot._napari._vispy import create_vispy_overlay


class QtViewerBase(QWidget):
    """Qt view for the napari Viewer model.

    Parameters
    ----------
    viewer : imimspy.napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    canvas : vispy.scene.SceneCanvas
        Canvas for rendering the current view.
    layer_to_visual : dict
        Dictionary mapping napari layers with their corresponding vispy_layers.
    view : vispy scene widget
        View displayed by vispy canvas. Adds a vispy ViewBox as a child widget.
    viewer :
        Napari viewer containing the rendered scene, layers, and controls.
    """

    _instances = WeakSet()

    def __init__(self, view, viewer, parent=None, disable_controls: bool = False, **kwargs):
        super().__init__(parent=parent)
        self._instances.add(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        if hasattr(Qt, "AA_UseStyleSheetPropagationInWidgetStyles"):
            QCoreApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)

        # handle to the viewer instance
        self.view = view
        self.viewer = viewer

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._key_bindings_dialog = None
        self._disable_controls = disable_controls
        self._layers_controls_dialog = None

        # This dictionary holds the corresponding vispy visual for each layer
        self.layer_to_visual = {}
        self.overlay_to_visual = {}

        # create ui widgets
        self._create_widgets(**kwargs)

        # create main vispy canvas
        self._create_canvas()

        # set ui
        self._set_layout(**kwargs)

        # activate layer change
        self._on_active_change()

        # setup events
        self._set_events()

        # add layers
        for layer in self.viewer.layers:
            self._add_layer(layer)

        # setup view
        self._set_view()

        # setup camera
        self._set_camera()

        # Add axes, scalebar, grid and colorbar visuals
        self._add_visuals()

        # add extra initialisation
        self._post_init()

    @property
    def grid_lines(self):
        """Grid lines."""
        return self.overlay_to_visual[self.viewer._overlays["grid_lines"]]

    @property
    def text_overlay(self):
        """Grid lines."""
        return self.overlay_to_visual[self.viewer._overlays["text"]]

    def _add_overlay(self, overlay: Overlay) -> None:
        vispy_overlay = create_vispy_overlay(overlay, viewer=self.viewer)

        if isinstance(overlay, CanvasOverlay):
            vispy_overlay.node.parent = self.view
        elif isinstance(overlay, SceneOverlay):
            vispy_overlay.node.parent = self.view.scene
        self.overlay_to_visual[overlay] = vispy_overlay

    def __getattr__(self, name):
        return object.__getattribute__(self, name)

    @property
    def pos_offset(self) -> Tuple[int, int]:
        """Window offset."""
        return 0, 0

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        raise NotImplementedError("Must implement method")

    def enterEvent(self, event):
        """Emit our own event when mouse enters the canvas."""
        self.viewer.mouse_over_canvas = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Emit our own event when mouse leaves the canvas."""
        self.viewer.mouse_over_canvas = False
        super().leaveEvent(event)

    def _create_widgets(self, **kwargs):
        """Create ui widgets."""
        raise NotImplementedError("Must implement method")

    def _set_layout(self, **kwargs):
        # set in main canvas
        raise NotImplementedError("Must implement method")

    def _set_events(self):
        raise NotImplementedError("Must implement method")

    def _set_camera(self):
        pass

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar."""
        raise NotImplementedError("Must implement method")

    def _set_view(self):
        """Set view."""
        self.view = self.canvas.central_widget.add_view(border_width=0)

    def _post_init(self):
        """Complete initialization with post-init events."""

    def enterEvent(self, event):
        """Enable status on canvas enter"""
        self.viewer.status = "Ready"
        self.viewer.mouse_over_canvas = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Disable status on canvas leave"""
        self.viewer.status = ""
        self.viewer.mouse_over_canvas = False
        super().leaveEvent(event)

    def _constrain_width(self, _event):
        """Allow the layer controls to be wider, only if floated.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        if self.dockLayerControls.isFloating():
            self.controls.setMaximumWidth(700)
        else:
            self.controls.setMaximumWidth(220)

    def _on_active_change(self):
        """When active layer changes change keymap handler."""
        self._key_map_handler.keymap_providers = (
            [self.viewer]
            if self.viewer.layers.selection.active is None
            else [self.viewer.layers.selection.active, self.viewer]
        )

    def _on_add_layer_change(self, event):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        layer = event.value
        self._add_layer(layer)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        raise NotImplementedError("Must implement method")

    def on_save_figure(self, path=None):
        """Export figure."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self, history=[])
        if dialog.exec_():
            pass

    def _screenshot(self, size=None, scale=None, flash=True, canvas_only=False) -> QImage:
        """Capture screenshot of the currently displayed viewer.

        Parameters
        ----------
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        size : tuple (int, int)
            Size (resolution) of the screenshot. By default, the currently displayed size.
            Only used if `canvas_only` is True.
        scale : float
            Scale factor used to increase resolution of canvas for the screenshot. By default, the currently displayed
             resolution.
            Only used if `canvas_only` is True.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and
            if False include the napari viewer frame in the screenshot,
            By default, True.

        Returns
        -------
        img : QImage
        """
        from napari._qt.utils import add_flash_animation

        if canvas_only:
            canvas = self.canvas
            prev_size = canvas.size
            if size is not None:
                if len(size) != 2:
                    raise ValueError(f"screenshot size must be 2 values, got {len(size)}")
                # Scale the requested size to account for HiDPI
                size = tuple(int(dim / self.devicePixelRatio()) for dim in size)
                canvas.size = size[::-1]  # invert x ad y for vispy
            if scale is not None:
                # multiply canvas dimensions by the scale factor to get new size
                canvas.size = tuple(int(dim * scale) for dim in canvas.size)
            try:
                img = self.canvas.native.grabFramebuffer()
                if flash:
                    add_flash_animation(self)
            finally:
                # make sure we always go back to the right canvas size
                if size is not None or scale is not None:
                    canvas.size = prev_size
        else:
            img = self.grab().toImage()
            if flash:
                add_flash_animation(self)
        return img

    def screenshot(self, path=None, size=None, scale=None, flash=True, canvas_only=False):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.
        size : tuple (int, int)
            Size (resolution) of the screenshot. By default, the currently displayed size.
            Only used if `canvas_only` is True.
        scale : float
            Scale factor used to increase resolution of canvas for the screenshot. By default, the currently displayed resolution.
            Only used if `canvas_only` is True.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and
            if False include the napari viewer frame in the screenshot,
            By default, True.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from skimage.io import imsave

        img = QImg2array(self._screenshot(size=size, scale=scale, flash=flash, canvas_only=canvas_only))
        if path is not None:
            imsave(path, img)  # scikit-image imsave method
        return img

    def clipboard(self, size=None, scale=None, flash=True, canvas_only=True):
        """Take a screenshot of the currently displayed viewer and copy the image to the clipboard."""
        img = self._screenshot(size=size, scale=scale, flash=flash, canvas_only=canvas_only)

        cb = QGuiApplication.clipboard()
        cb.setImage(img)

    def on_open_controls_dialog(self, event=None) -> None:
        """Open dialog responsible for layer settings."""
        raise NotImplementedError("Must implement method")

    def on_toggle_controls_dialog(self, _event=None):
        """Toggle between on/off state of the layer settings."""
        if self._disable_controls:
            return
        if self._layers_controls_dialog is None:
            self.on_open_controls_dialog()
        else:
            self._layers_controls_dialog.setVisible(not self._layers_controls_dialog.isVisible())

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

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        raise NotImplementedError("Must implement method")
