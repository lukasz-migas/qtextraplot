"""Shared helpers for custom Qt viewer widgets."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from qtpy.QtWidgets import QApplication, QWidget

if ty.TYPE_CHECKING:
    from qtpy.QtCore import QEvent


class QtViewerInstanceTracker:
    """Track live Qt viewer instances and the most recently active one."""

    _instances: ty.ClassVar[list[QWidget]] = []
    _instance_index: ty.ClassVar[int] = -1

    @classmethod
    def set_current_index(cls, index_or_widget: int | QWidget) -> None:
        """Set the current active viewer index."""
        if isinstance(index_or_widget, QWidget):
            index_or_widget = cls._instances.index(index_or_widget)
        cls._instance_index = index_or_widget

    @classmethod
    def current(cls) -> QWidget | None:
        """Return the current viewer instance, if any."""
        if not cls._instances:
            return None
        return cls._instances[cls._instance_index]

    def _register_instance(self, *registries: list[QWidget]) -> None:
        """Register the widget with all instance registries it participates in."""
        self._instances.append(self)
        for registry in registries:
            registry.append(self)
        self.current_index = len(self._instances) - 1


def calc_status_from_cursor(viewer) -> tuple[str | dict, str] | None:
    """Build status and tooltip text from the current cursor position."""
    if not viewer.mouse_over_canvas:
        return None

    active = viewer.layers.selection.active
    if active is not None and active._loaded:
        status = active.get_status(
            viewer.cursor.position,
            view_direction=viewer.cursor._view_direction,
            dims_displayed=list(viewer.dims.displayed),
            world=True,
        )
        tooltip_text = ""
        if viewer.tooltip.visible:
            tooltip_text = active._get_tooltip_text(
                np.asarray(viewer.cursor.position),
                view_direction=np.asarray(viewer.cursor._view_direction),
                dims_displayed=list(viewer.dims.displayed),
                world=True,
            )
        return status, tooltip_text

    x, y = viewer.cursor.position
    status = f"[{round(x)} {round(y)}]"
    return status, status


def set_mouse_over_status(viewer, active: bool) -> None:
    """Update viewer status when the pointer enters or leaves the canvas."""
    viewer.status = "Ready" if active else ""
    viewer.mouse_over_canvas = active


def show_controls_dialog(widget, dialog_type: type[QWidget]) -> None:
    """Create and present the controls dialog if controls are enabled."""
    if widget._disable_controls:
        return

    if widget._layers_controls_dialog is None:
        widget._layers_controls_dialog = dialog_type(widget)
    widget._layers_controls_dialog.show()
    widget._layers_controls_dialog.raise_()
    widget._layers_controls_dialog.activateWindow()


def toggle_controls_dialog(widget, opener: ty.Callable[[], None]) -> None:
    """Toggle the visibility of the controls dialog."""
    if widget._disable_controls:
        return
    if widget._layers_controls_dialog is None:
        opener()
        return
    widget._layers_controls_dialog.setVisible(not widget._layers_controls_dialog.isVisible())


def copy_screenshot_to_clipboard(
    screenshot: ty.Callable[..., ty.Any],
    *,
    size: tuple[int, int] | None = None,
    scale: float | None = None,
    flash: bool = True,
    canvas_only: bool = False,
    fit_to_data_extent: bool = False,
) -> None:
    """Capture a screenshot and copy it to the clipboard."""
    img = screenshot(
        flash=flash,
        canvas_only=canvas_only,
        size=size,
        scale=scale,
        fit_to_data_extent=fit_to_data_extent,
    )
    QApplication.clipboard().setImage(img)


def cleanup_qt_viewer(
    event: QEvent,
    *,
    canvas_native,
    dims=None,
    disconnect: ty.Callable[[], None] | None = None,
) -> None:
    """Perform shared viewer cleanup before the widget closes."""
    if dims is not None:
        dims.stop()
    if disconnect is not None:
        with suppress(TypeError, RuntimeError):
            disconnect()
    canvas_native.deleteLater()
    event.accept()
