"""Grid controls."""

from __future__ import annotations

import qtextra.helpers as hp
from napari._qt.widgets.qt_spinbox import QtSpinBox
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QWidget

from qtextraplot._napari._enums import ViewerType


class QtGridControls(QtFramelessPopup):
    def __init__(self, viewer: ViewerType, parent: QWidget | None = None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("gridControls")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        shape_help_msg = (
            "Number of rows and columns in the grid. A value of -1 for either or both of width and height will\n"
            " trigger an auto calculation of the necessary grid shape to appropriately fill all the layers at the\n"
            " appropriate stride. 0 is not a valid entry."
        )

        stride_help_msg = (
            "Number of layers to place in each grid square before moving on to the next square. The default ordering\n"
            " is to place the most visible layer in the top left corner of the grid. A negative stride will cause the\n"
            " order in which the layers are placed in the grid to be reversed. 0 is not a valid entry."
        )

        spacing_help_msg = (
            "The amount of spacing between grid viewboxes.\n"
            "If between 0 and 1, it is interpreted as a proportion of the size of the viewboxes.\n"
            "If equal or greater than 1, it is interpreted as screen pixels."
        )

        # set up
        stride_min = self.viewer.grid.__fields__["stride"].type_.ge
        stride_max = self.viewer.grid.__fields__["stride"].type_.le
        stride_not = self.viewer.grid.__fields__["stride"].type_.ne
        grid_stride = QtSpinBox(self)
        grid_stride.setObjectName("gridStrideBox")
        grid_stride.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_stride.setRange(stride_min, stride_max)
        grid_stride.setProhibitValue(stride_not)
        grid_stride.setValue(self.viewer.grid.stride)
        grid_stride.valueChanged.connect(self._update_grid_stride)

        width_min = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ge
        width_not = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ne
        grid_width = QtSpinBox(self)
        grid_width.setObjectName("gridWidthBox")
        grid_width.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_width.setMinimum(width_min)
        grid_width.setProhibitValue(width_not)
        grid_width.setValue(self.viewer.grid.shape[1])
        grid_width.valueChanged.connect(self._update_grid_width)

        height_min = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ge
        height_not = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ne
        grid_height = QtSpinBox(self)
        grid_height.setObjectName("gridStrideBox")
        grid_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_height.setMinimum(height_min)
        grid_height.setProhibitValue(height_not)
        grid_height.setValue(self.viewer.grid.shape[0])
        grid_height.valueChanged.connect(self._update_grid_height)

        # set up spacing
        spacing_min = self.viewer.grid.__fields__["spacing"].type_.ge
        spacing_max = self.viewer.grid.__fields__["spacing"].type_.le
        spacing_step = self.viewer.grid.__fields__["spacing"].type_.step
        grid_spacing = QDoubleSpinBox(self)
        grid_spacing.setObjectName("gridSpacingBox")
        grid_spacing.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_spacing.setMinimum(spacing_min)
        grid_spacing.setMaximum(spacing_max)
        grid_spacing.setValue(self.viewer.grid.spacing)
        grid_spacing.setDecimals(2)
        grid_spacing.setSingleStep(spacing_step)
        grid_spacing.valueChanged.connect(self._update_grid_spacing)
        self.grid_spacing_box = grid_spacing

        # layout
        layout = hp.make_form_layout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.insertRow(
            0,
            QLabel("Grid stride:"),
            hp.make_h_layout(grid_stride, hp.make_help_label(self, stride_help_msg), stretch_id=0),
        )
        layout.insertRow(
            1,
            QLabel("Grid width:"),
            hp.make_h_layout(grid_width, hp.make_help_label(self, shape_help_msg), stretch_id=0),
        )
        layout.insertRow(
            2,
            QLabel("Grid height:"),
            hp.make_h_layout(grid_height, hp.make_help_label(self, shape_help_msg), stretch_id=0),
        )
        layout.insertRow(
            3,
            QLabel("Grid spacing:"),
            hp.make_h_layout(grid_spacing, hp.make_help_label(self, spacing_help_msg), stretch_id=0),
        )
        return layout

    def _update_grid_width(self, value):
        """Update the width value in grid shape."""
        self.viewer.grid.shape = (self.viewer.grid.shape[0], value)

    def _update_grid_stride(self, value):
        """Update stride in grid settings."""
        self.viewer.grid.stride = value

    def _update_grid_height(self, value):
        """Update height value in grid shape."""
        self.viewer.grid.shape = (value, self.viewer.grid.shape[1])

    def _update_grid_spacing(self, value: float) -> None:
        """Update spacing value in grid settings."""
        self.viewer.grid.spacing = value
