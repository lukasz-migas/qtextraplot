"""Helper functions."""

from __future__ import annotations

import qtextra.helpers as hp
import qtpy.QtWidgets as Qw
from qtextra.typing import Callback
from qtpy.QtGui import QImage, QPixmap

try:
    from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
    from napari.utils.events.custom_types import Array
except ImportError:
    Array = None
    QtColormapComboBox = None


def make_colormap_combobox(
    parent: Qw.QWidget | None,
    func: Callback | None = None,
    default: str = "magma",
    label_min_width: int = 0,
) -> tuple[QtColormapComboBox, Qw.QHBoxLayout]:
    """Make colormap combobox."""
    from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
    from napari.utils.colormaps import AVAILABLE_COLORMAPS

    def _update_colormap(value):
        colormap = AVAILABLE_COLORMAPS[value]
        cbar = colormap.colorbar
        # Note that QImage expects the image width followed by height
        image = QImage(
            cbar,
            cbar.shape[1],
            cbar.shape[0],
            QImage.Format.Format_RGBA8888,
        )
        widget_label.setPixmap(QPixmap.fromImage(image))

    widget_label = hp.make_label(parent, "", object_name="colorbar")
    widget_label.setScaledContents(True)
    if label_min_width:
        widget_label.setMinimumWidth(label_min_width)
    widget = QtColormapComboBox(parent)
    widget.currentTextChanged.connect(_update_colormap)
    widget.setObjectName("colormapComboBox")
    widget.addItems(AVAILABLE_COLORMAPS)
    widget._allitems = set(AVAILABLE_COLORMAPS)
    widget.setCurrentText(default)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in hp._validate_func(func)]
    return widget, hp.make_h_layout(widget_label, widget, stretch_id=[1], spacing=0)


def make_colormap_combobox_alone(
    parent: Qw.QWidget | None = None,
    func: Callback | None = None,
    default: str = "magma",
) -> QtColormapComboBox:
    """Make colormap combobox."""
    from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
    from napari.utils.colormaps import AVAILABLE_COLORMAPS

    widget = QtColormapComboBox(parent)
    widget.setObjectName("colormapComboBox")
    widget.addItems(AVAILABLE_COLORMAPS)
    widget._allitems = set(AVAILABLE_COLORMAPS)
    widget.setCurrentText(default)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in hp._validate_func(func)]
    return widget
