"""Take screenshot dialog."""

from __future__ import annotations

import typing as ty
from functools import partial

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtpy.QtWidgets import QLayout

if ty.TYPE_CHECKING:
    from qtextraplot._napari.image.qt_viewer import QtViewer as ImageQtViewer
    from qtextraplot._napari.line.wrapper import NapariLineView


class QtScreenshotDialog(QtFramelessPopup):
    """Popup to control screenshot/clipboard."""

    def __init__(self, wrapper: ImageQtViewer | NapariLineView, parent=None):
        self.qt_viewer = wrapper
        super().__init__(parent=parent)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make layout."""
        size = self.qt_viewer.canvas._scene_canvas.size
        self.size_x = hp.make_int_spin_box(
            self,
            50,
            8000,
            50,
            default=size[0],
            tooltip="Width of the screenshot.",
        )
        self.size_y = hp.make_int_spin_box(
            self,
            50,
            8000,
            50,
            default=size[1],
            tooltip="Height of the screenshot.",
        )

        self.scale = hp.make_double_spin_box(
            self,
            0.1,
            5,
            0.5,
            n_decimals=2,
            default=1,
            tooltip="Increase the resolution of the screenshot. Value of 1.0 means that the screenshot will have the"
            " same resolution as the canvas, whereas, values >1 will increase the resolution by the specified ratio."
            " The higher this value is, the longer it will take to generate the screenshot.",
        )
        self.canvas_only = hp.make_checkbox(
            self,
            "",
            "Only screenshot the canvas",
            value=True,
        )

        layout = hp.make_form_layout(margin=(6, 6, 6, 6))
        layout.addRow(self._make_move_handle("Screenshot controls"))
        layout.addRow("Width", self.size_x)
        layout.addRow("Height", self.size_y)
        layout.addRow("Up-sample", self.scale)
        layout.addRow("Canvas only", self.canvas_only)
        layout.addRow(
            hp.make_btn(
                self,
                "Copy to clipboard",
                tooltip="Copy screenshot to clipboard",
                func=self.on_copy_to_clipboard,
            )
        )
        layout.addRow(
            hp.make_btn(
                self,
                "Save to file",
                tooltip="Save screenshot to file",
                func=self.on_save_figure,
            )
        )
        return layout

    def on_save_figure(self) -> None:
        """Save figure."""
        from napari._qt.dialogs.screenshot_dialog import HOME_DIRECTORY, ScreenshotDialog

        save_func = partial(
            self.qt_viewer.screenshot,
            size=(self.size_y.value(), self.size_x.value()),
            scale=self.scale.value(),
            canvas_only=self.canvas_only.isChecked(),
        )

        dialog = ScreenshotDialog(save_func, self.parent() or self, HOME_DIRECTORY, history=[])
        if dialog.exec_():
            pass

    def on_copy_to_clipboard(self) -> None:
        """Copy canvas to clipboard."""
        self.qt_viewer.clipboard(
            size=(self.size_y.value(), self.size_x.value()),
            scale=self.scale.value(),
            canvas_only=self.canvas_only.isChecked(),
        )
