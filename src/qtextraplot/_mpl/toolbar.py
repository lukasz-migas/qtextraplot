"""Toolbar for MPL-based plots."""

import typing as ty

from qtextra.helpers import add_flash_animation
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar
from qtpy.QtCore import Qt

if ty.TYPE_CHECKING:
    from qtextraplot._mpl import ViewMplLine


class MplToolbar(QtMiniToolbar):
    """Toolbar."""

    def __init__(self, view: "ViewMplLine", parent):
        super().__init__(parent=parent, orientation=Qt.Orientation.Vertical, add_spacer=False)
        self.view = view

        # view reset/clear
        self.tools_erase_btn = self.insert_qta_tool("erase", tooltip="Clear image", func=view.clear)
        self.tools_erase_btn.hide()
        self.tools_zoomout_btn = self.insert_qta_tool("zoom_out", tooltip="Zoom-out", func=view.on_zoom_out)
        self.tools_clip_btn = self.insert_qta_tool(
            "screenshot",
            tooltip="Copy figure to clipboard",
            func=self.on_copy_to_clipboard,
        )
        self.tools_save_btn = self.insert_qta_tool(
            "save",
            tooltip="Save figure",
            func=view.on_save_figure,
        )
        self.add_spacer()

    def on_copy_to_clipboard(self):
        """Copy figure to clipboard."""
        add_flash_animation(self.view.widget)
        self.view.copy_to_clipboard()
