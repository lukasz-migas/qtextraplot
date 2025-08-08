"""Camera controls for the napari viewer."""

from __future__ import annotations

from functools import partial

import qtextra.helpers as hp
from napari.utils.camera_orientations import (
    DepthAxisOrientation,
    DepthAxisOrientationStr,
    HorizontalAxisOrientation,
    HorizontalAxisOrientationStr,
    VerticalAxisOrientation,
    VerticalAxisOrientationStr,
)
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QGridLayout, QHBoxLayout, QLabel, QWidget

from qtextraplot._napari._enums import ViewerType


class QtCameraControls(QtFramelessPopup):
    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("gridControls")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(5, 5, 5, 5)

        # Add orientation controls
        self._add_orientation_controls(grid_layout)

        # Add shared camera controls
        self._add_shared_camera_controls(grid_layout)

        # Add 3D camera controls if in 3D mode
        if self.viewer.dims.ndisplay == 3:
            self._add_3d_camera_controls(grid_layout)

        return grid_layout

    def _add_3d_camera_controls(self, grid_layout: QGridLayout) -> None:
        """Add 3D camera controls to the popup."""
        self.perspective = hp.make_double_slider_with_text(
            parent=self,
            value=self.viewer.camera.perspective,
            value_range=(0, 90),
            func=self._update_perspective,
        )

        perspective_help_symbol = hp.make_help_label(
            self,
            "Controls perspective projection strength. 0 is orthographic, larger values increase perspective effect.",
        )

        self.rx = hp.make_double_slider_with_text(
            parent=self,
            value=self.viewer.camera.angles[0],
            value_range=(-180, 180),
            func=partial(self._update_camera_angles, 0),
        )

        self.ry = hp.make_double_slider_with_text(
            parent=self,
            value=self.viewer.camera.angles[1],
            value_range=(-89, 89),
            func=partial(self._update_camera_angles, 1),
        )

        self.rz = hp.make_double_slider_with_text(
            parent=self,
            value=self.viewer.camera.angles[2],
            value_range=(-180, 180),
            func=partial(self._update_camera_angles, 2),
        )

        angle_help_symbol = hp.make_help_label(
            self,
            "Controls the rotation angles around each axis in degrees.",
        )

        grid_layout.addWidget(QLabel("Perspective:"), 2, 0)
        grid_layout.addWidget(self.perspective, 2, 1)
        grid_layout.addWidget(perspective_help_symbol, 2, 2)

        grid_layout.addWidget(QLabel("Angles    X:"), 3, 0)
        grid_layout.addWidget(self.rx, 3, 1)
        grid_layout.addWidget(angle_help_symbol, 3, 2)

        grid_layout.addWidget(QLabel("             Y:"), 4, 0)
        grid_layout.addWidget(self.ry, 4, 1)

        grid_layout.addWidget(QLabel("             Z:"), 5, 0)
        grid_layout.addWidget(self.rz, 5, 1)

    def _add_shared_camera_controls(self, grid_layout: QGridLayout) -> None:
        """Add shared hp.make_double_slider_with_text controls to the popup."""
        self.zoom = hp.make_double_slider_with_text(
            parent=self,
            value=self.viewer.camera.zoom,
            value_range=(0.01, 100),
            n_decimals=2,
            func=self._update_zoom,
        )

        zoom_help_symbol = hp.make_help_label(
            self,
            "Controls zoom level of the camera. Larger values zoom in, smaller values zoom out.",
        )

        grid_layout.addWidget(QLabel("Zoom:"), 1, 0)
        grid_layout.addWidget(self.zoom, 1, 1)
        grid_layout.addWidget(zoom_help_symbol, 1, 2)

    def _add_orientation_controls(self, grid_layout: QGridLayout) -> None:
        """Add orientation controls to the popup."""
        orientation_widget = QWidget(self)
        orientation_layout = QHBoxLayout(orientation_widget)
        orientation_layout.setContentsMargins(0, 0, 0, 0)

        self.vertical_combo = hp.make_enum_combobox(
            parent=self,
            enum_class=VerticalAxisOrientation,
            current_enum=self.viewer.camera.orientation[1],
            callback=partial(self._update_orientation, VerticalAxisOrientation),
        )

        self.horizontal_combo = hp.make_enum_combobox(
            parent=self,
            enum_class=HorizontalAxisOrientation,
            current_enum=self.viewer.camera.orientation[2],
            callback=partial(self._update_orientation, HorizontalAxisOrientation),
        )

        if self.viewer.dims.ndisplay == 2:
            orientation_layout.addWidget(self.vertical_combo)
            orientation_layout.addWidget(self.horizontal_combo)
            self.orientation_help_symbol = hp.make_help_label(
                self,
                "Controls the orientation of the vertical and horizontal camera axes.",
            )

        else:
            self.depth_combo = hp.make_enum_combobox(
                parent=self,
                enum_class=DepthAxisOrientation,
                current_enum=self.viewer.camera.orientation[0],
                callback=partial(self._update_orientation, DepthAxisOrientation),
            )

            orientation_layout.addWidget(self.depth_combo)
            orientation_layout.addWidget(self.vertical_combo)
            orientation_layout.addWidget(self.horizontal_combo)

            self.orientation_help_symbol = hp.make_help_label(
                self,
                "",  # updated dynamically
            )
            self._update_handedness_help_symbol()
            self.viewer.camera.events.orientation.connect(self._update_handedness_help_symbol)

        grid_layout.addWidget(QLabel("Orientation:"), 0, 0)
        grid_layout.addWidget(orientation_widget, 0, 1)
        grid_layout.addWidget(self.orientation_help_symbol, 0, 2)

    def _update_handedness_help_symbol(self, event=None) -> None:
        """Update the handedness symbol based on the camera orientation."""
        handedness = self.viewer.camera.handedness
        tooltip_text = (
            "Controls the orientation of the depth, vertical, and horizontal camera axes.\n"
            "Default is right-handed (towards, down, right).\n"
            "Default prior to 0.6.0 was left-handed (away, down, right).\n"
            f"Currently orientation is {handedness.value}-handed."
        )
        self.orientation_help_symbol.setToolTip(tooltip_text)
        self.orientation_help_symbol.set_qta("left_hand" if handedness.value == "left" else "right_hand")

    def _update_orientation(
        self,
        orientation_type: type[DepthAxisOrientation | VerticalAxisOrientation | HorizontalAxisOrientation],
        orientation_value: (DepthAxisOrientationStr | VerticalAxisOrientationStr | HorizontalAxisOrientationStr),
    ) -> None:
        """Update the orientation of the camera."""
        axes = (
            DepthAxisOrientation,
            VerticalAxisOrientation,
            HorizontalAxisOrientation,
        )
        axis_to_update = axes.index(orientation_type)
        new_orientation = list(self.viewer.camera.orientation)
        new_orientation[axis_to_update] = orientation_type(orientation_value)
        self.viewer.camera.orientation = tuple(new_orientation)

    def _update_camera_angles(self, idx: int, value: float) -> None:
        """Update the camera angles."""
        angles = list(self.viewer.camera.angles)
        angles[idx] = value
        self.viewer.camera.angles = tuple(angles)

    def _update_zoom(self, value: float) -> None:
        """Update the camera zoom."""
        self.viewer.camera.zoom = value

    def _update_perspective(self, value: float) -> None:
        """Update the camera perspective."""
        self.viewer.camera.perspective = value
