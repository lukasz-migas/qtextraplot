"""Layer buttons."""

from __future__ import annotations

import typing as ty
from functools import partial

import qtextra.helpers as hp
from napari._qt.dialogs.qt_modal import QtPopup
from napari._qt.widgets.qt_dims_sorter import QtDimsSorter
from napari.utils.action_manager import action_manager
from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import QApplication, QFrame, QHBoxLayout, QWidget

if ty.TYPE_CHECKING:
    from qtextraplot._napari.image.components.viewer_model import Viewer


def add_new_points(viewer):
    viewer.add_points(
        ndim=max(viewer.dims.ndim, 2),
        scale=viewer.layers.extent.step,
    )


def add_new_shapes(viewer):
    viewer.add_shapes(
        ndim=max(viewer.dims.ndim, 2),
        scale=viewer.layers.extent.step,
    )


def make_qta_btn(
    parent: QWidget, icon_name: str, tooltip: str = "", action: str = "", extra_tooltip_text: str = "", **kwargs: ty.Any
) -> QtImagePushButton:
    """Make a button with an icon from QtAwesome."""
    btn = hp.make_qta_btn(parent=parent, icon_name=icon_name, tooltip=tooltip, **kwargs)
    btn.set_normal()
    btn.setProperty("layer_button", True)
    if action:
        action_manager.bind_button(action, btn, extra_tooltip_text=extra_tooltip_text)
    return btn


class QtLayerButtons(QFrame):
    """Button controls for napari layers."""

    def __init__(self, qt_viewer, viewer: Viewer, disable_new_layers: bool = False, **_kwargs: ty.Any):
        super().__init__()
        self.qt_viewer = qt_viewer
        self.viewer = viewer
        self.delete_btn = make_qta_btn(
            self,
            "delete",
            action="napari:delete_selected_layers",
        )
        self.delete_btn.setParent(self)

        self.new_points_btn = make_qta_btn(
            self,
            "new_points",
            "Add new points layer",
            func=partial(add_new_points, self.viewer),
        )
        self.new_shapes_btn = make_qta_btn(
            self,
            "new_shapes",
            "Add new shapes layer",
            func=partial(add_new_shapes, self.viewer),
        )
        self.new_labels_btn = make_qta_btn(
            self,
            "new_labels",
            "Add new free-hand draw shapes layer",
            func=self.viewer._new_labels,
        )
        if disable_new_layers:
            self.new_points_btn.hide()
            self.new_shapes_btn.hide()
            self.new_labels_btn.hide()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_labels_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)
        self.setLayout(layout)

    def enterEvent(self, event):
        """Emit our own event when mouse enters the canvas."""
        from qtextraplot._napari.image.qt_viewer import QtViewer

        QtViewer.set_current_index(self.qt_viewer.current_index)
        super().enterEvent(event)


class QtViewerButtons(QFrame):
    """Button controls for the napari viewer."""

    def __init__(self, qt_viewer, viewer, **_kwargs: ty.Any):
        super().__init__()
        self.qt_viewer = qt_viewer
        self.viewer = viewer

        self.ndisplayButton = make_qta_btn(
            self,
            "ndisplay_off",
            "Toggle number of displayed dimensions",
            checkable=True,
            checked=self.viewer.dims.ndisplay == 3,
            checked_icon_name="ndisplay_on",
            action="napari:toggle_ndisplay",
            func_menu=self.open_perspective_popup,
        )

        self.rollDimsButton = make_qta_btn(
            self,
            "roll",
            "Roll dimensions order for display. Right-click on the button to manually order dimensions.",
            action="napari:roll_axes",
            func_menu=self.open_roll_popup,
        )

        self.transposeDimsButton = make_qta_btn(
            self,
            "transpose",
            "Transpose displayed dimensions.",
            action="napari:transpose_axes",
        )
        self.transposeDimsButton.installEventFilter(self)

        self.gridViewButton = make_qta_btn(
            self,
            "grid_off",
            "Toggle grid view. Right-click on the button to change grid settings.",
            checkable=True,
            checked=viewer.grid.enabled,
            checked_icon_name="grid_on",
            action="napari:toggle_grid",
            func_menu=self.open_grid_popup,
        )

        @self.viewer.grid.events.enabled.connect
        def _set_grid_mode_checkstate(event):
            self.gridViewButton.setChecked(event.value)

        self.resetViewButton = make_qta_btn(
            self,
            "zoom_out",
            "Reset view",
            action="napari:reset_view",
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.ndisplayButton)
        layout.addWidget(self.rollDimsButton)
        layout.addWidget(self.transposeDimsButton)
        layout.addWidget(self.gridViewButton)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
        self.setLayout(layout)

    def enterEvent(self, event):
        """Emit our own event when mouse enters the canvas."""
        from qtextraplot._napari.image.qt_viewer import QtViewer

        QtViewer.set_current_index(self.qt_viewer.current_index)
        super().enterEvent(event)

    def eventFilter(self, qobject, event):
        """Have Alt/Option key rotate layers with the transpose button."""
        modifiers = QApplication.keyboardModifiers()
        if (
            modifiers == Qt.KeyboardModifier.AltModifier
            and qobject == self.transposeDimsButton
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            action_manager.trigger("napari:rotate_layers")
            return True
        return False

    def open_roll_popup(self):
        """Open a grid popup to manually order the dimensions."""
        dim_sorter = QtDimsSorter(self.viewer.dims, self)
        dim_sorter.setObjectName("dim_sorter")
        dim_sorter.layout().setContentsMargins(0, 0, 0, 0)

        # make layout
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(dim_sorter)

        # popup and show
        pop = QtPopup(self)
        pop.frame.setLayout(layout)
        pop.show_above_mouse()

    def open_perspective_popup(self):
        """Show a slider to control the viewer `camera.perspective`."""
        from qtextraplot._napari.component_controls.qt_camera_controls import QtCameraControls

        dlg = QtCameraControls(self.viewer, self)
        dlg.show_above_widget(self.gridViewButton)

    def open_grid_popup(self):
        """Open the grid options pop up widget."""
        from qtextraplot._napari.component_controls.qt_grid_controls import QtGridControls

        dlg = QtGridControls(self.viewer, self)
        dlg.show_above_widget(self.gridViewButton)
