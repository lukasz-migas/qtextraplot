"""Mixin classes."""

from __future__ import annotations

import typing as ty

if ty.TYPE_CHECKING:
    from qtextraplot._napari.image.wrapper import NapariImageView
    from qtextraplot._napari.line.wrapper import NapariLineView


class NapariMixin:
    """Plotting mixins."""

    _views_1d: list[NapariLineView] | None = None
    _views_2d: list[NapariImageView] | None = None

    def _register_views(self, views_1d: list | None = None, views_2d: list | None = None) -> None:
        """Register views."""
        if self._views_1d is None:
            self._views_1d = []
        if views_1d:
            self._views_1d.extend(views_1d)
        if self._views_2d is None:
            self._views_2d = []
        if views_2d:
            self._views_2d.extend(views_2d)

    def _update_after_activate(self) -> None:
        """"Method is called just after user requested to see this widget.

        It is necessary in order to force updates in the vispy canvas which is otherwise not updated when the panel
        is not visible.
        """
        if self._views_2d:
            for view_2d in self._views_2d:
                view_2d.widget.canvas.native.update()

        # try to fix axes issues
        if self._views_1d:
            for view_1d in self._views_1d:
                view_1d.widget.canvas.native.update()
                xmin, xmax, ymin, ymax = view_1d.viewer.camera.rect
                view_1d.viewer.camera.rect = xmin + 1, xmax, ymin, ymax
                view_1d.viewer.camera.rect = xmin, xmax, ymin, ymax
