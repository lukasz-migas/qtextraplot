"""Reusable Qt widgets for qtextraplot."""

from __future__ import annotations

import typing as ty

import numpy as np
import qtextra.helpers as hp
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QColor, QIcon, QImage, QMouseEvent, QPixmap
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget


class QtColormapButton(QPushButton):
    """Icon-sized button that previews and selects napari colormaps."""

    evt_colormap_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None, colormap: str = "magma") -> None:
        super().__init__(parent)
        self._colormap = ""
        self._popup: _ColormapPopup | None = None
        self._color_popup: QWidget | None = None
        self.setFixedSize(26, 22)
        self.setToolTip("Select colormap. Right-click to create a custom color.")
        self.clicked.connect(self.show_colormap_popup)
        self.set_colormap(colormap)

    def current_colormap(self) -> str:
        """Return the current colormap name."""
        return self._colormap

    def set_colormap(self, name: str) -> None:
        """Set the current colormap and update the preview icon."""
        available_colormaps = _available_colormaps()
        name = name if name in available_colormaps else "magma"
        if name == self._colormap:
            self._update_icon()
            return
        self._colormap = name
        self._update_icon()
        self.evt_colormap_changed.emit(name)

    def set_custom_color(self, color: ty.Any) -> None:
        """Create and select a single-color napari colormap."""
        qcolor = color if isinstance(color, QColor) else QColor(color)
        if not qcolor.isValid():
            return
        rgba = np.asarray(qcolor.getRgbF(), dtype=np.float32)
        colors = np.vstack((np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32), rgba))
        color_name = qcolor.name(
            QColor.NameFormat.HexArgb if qcolor.alpha() < 255 else QColor.NameFormat.HexRgb,
        ).lower()
        colormap_name = f"custom {color_name}"
        from napari.utils.colormaps import Colormap

        _available_colormaps()[colormap_name] = Colormap(
            colors,
            display_name=colormap_name,
            name=colormap_name,
        )
        self.set_colormap(colormap_name)

    def show_colormap_popup(self) -> None:
        """Show the colormap selector popup and open its option list."""
        if self._popup is None:
            self._popup = _ColormapPopup(self)
        self._popup.set_colormap(self._colormap)
        self._popup.move(self.mapToGlobal(self.rect().bottomLeft()))
        self._popup.show()
        self._popup.raise_()
        QTimer.singleShot(0, self._popup.show_colormap_list)

    def show_custom_color_popup(self) -> None:
        """Show napari's color picker and convert the selected color to a colormap."""
        from napari._qt.widgets.qt_color_swatch import QColorPopup

        self._color_popup = QColorPopup(self, self._current_qcolor())
        self._color_popup.colorSelected.connect(self.set_custom_color)
        self._color_popup.show_right_of_mouse()

    def _update_icon(self) -> None:
        """Update the button icon from the colormap colorbar."""
        colormap = _available_colormaps()[self._colormap]
        colorbar = colormap.colorbar
        image = QImage(
            colorbar,
            colorbar.shape[1],
            colorbar.shape[0],
            QImage.Format.Format_RGBA8888,
        )
        pixmap = QPixmap.fromImage(image).scaled(
            22,
            14,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setIcon(QIcon(pixmap))
        self.setIconSize(pixmap.size())

    def _current_qcolor(self) -> QColor:
        """Return the high color from the current colormap as a QColor."""
        colormap = _available_colormaps()[self._colormap]
        colors = np.asarray(colormap.colors, dtype=float)
        rgba = colors[-1] if colors.size else np.asarray([1.0, 1.0, 1.0, 1.0], dtype=float)
        rgba = np.clip(rgba, 0.0, 1.0)
        return QColor.fromRgbF(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3]))

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        """Open the custom-color picker on right-click."""
        if event is not None and event.button() == Qt.MouseButton.RightButton:
            self.show_custom_color_popup()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class _ColormapPopup(QWidget):
    """Popup containing a napari colormap combobox."""

    def __init__(self, button: QtColormapButton) -> None:
        super().__init__(button, Qt.WindowType.Popup)
        self._button = button
        from qtextraplot.helpers import make_colormap_combobox

        self.combobox, combobox_layout = make_colormap_combobox(
            self,
            func=self._on_colormap_changed,
            default=button.current_colormap(),
            label_min_width=96,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.addLayout(combobox_layout)

    def set_colormap(self, name: str) -> None:
        """Synchronize the popup combobox with the button colormap."""
        if self.combobox.findText(name) < 0 and name in _available_colormaps():
            self.combobox.addItem(name)
            if hasattr(self.combobox, "_allitems"):
                self.combobox._allitems.add(name)
        with hp.qt_signals_blocked(self.combobox):
            self.combobox.setCurrentText(name)

    def show_colormap_list(self) -> None:
        """Open the embedded combobox popup."""
        self.combobox.showPopup()

    def _on_colormap_changed(self, name: ty.Any) -> None:
        """Update the owner button when a colormap is selected."""
        self._button.set_colormap(str(name))
        self.hide()


def _available_colormaps() -> ty.Mapping[str, ty.Any]:
    """Return napari colormaps when the optional napari stack is available."""
    from napari.utils.colormaps import AVAILABLE_COLORMAPS

    return AVAILABLE_COLORMAPS
