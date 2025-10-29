"""Utility functions to handle mouse actions in NapariLineView."""

from __future__ import annotations

import typing as ty

import qtextra.helpers as hp

if ty.TYPE_CHECKING:
    from qtextraplot._napari.line.wrapper import NapariLineView, Viewer


def install_auto_scale_checkbox(view: NapariLineView) -> None:
    """Adds a checkbox to the layout."""

    def on_enable_auto_zoom(checked: bool) -> None:
        """Enable/disable automatic zoom on the data range."""
        view.config.auto_zoom = checked

    def on_auto_zoom() -> None:
        """Automatically zoom on the data range."""
        if view.config.auto_zoom:
            with view.viewer.camera.events.zoomed.blocker():
                view.viewer.reset_current_y_view()

    def on_update_state(event: ty.Any) -> None:
        """Update the state of the button."""
        with hp.qt_signals_blocked(toolbar.auto_btn):
            toolbar.auto_btn.setChecked(event.value)

    toolbar = view.widget.viewer_left_toolbar
    toolbar.auto_btn = toolbar.insert_qta_tool(
        "auto",
        tooltip="Enable/disable automatic zoom on the data range.",
        checkable=True,
        check=view.config.auto_zoom,
        func=on_enable_auto_zoom,
    )
    # handle initial state when the state changes
    view.config.events.auto_zoom.connect(on_update_state)
    view.config.events.auto_zoom.connect(on_auto_zoom)
    # connect to zoomed event
    view.viewer.camera.events.zoomed.connect(on_auto_zoom)


def install_double_click_to_zoom_out(view: NapariLineView) -> None:
    """Install double click to zoom out."""

    def on_double_click(viewer: Viewer, event: ty.Any) -> None:
        """Zoom out on double-click."""
        if event.button != 1:
            return
        view.viewer.reset_view()

    view.viewer.mouse_double_click_callbacks.append(on_double_click)
