"""View wrappers for the internal VisPy backend."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.secret import get_short_hash
from qtpy.QtCore import QMutexLocker

from qtextraplot._vispy.base import PlotLine, PlotScatter
from qtextraplot.utils.views_base import MUTEX, ViewBase


class _BaseVispyView(ViewBase):
    """Common functionality shared by VisPy-backed views."""

    IS_VISPY = True
    figure: ty.Any
    widget: ty.Any

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.figure = self._create_figure(parent, *args, **kwargs)
        self.widget = self.figure.native

    def _create_figure(self, parent, *args, **kwargs):
        raise NotImplementedError("Must implement method")

    def _cache_xy(self, x, y, **kwargs) -> None:
        self._data.update(x=np.asarray(x), y=np.asarray(y))
        self._plt_kwargs = dict(kwargs)

    def reset(self):
        """Reset the view from cached data."""
        self.light_clear()
        if "x" in self._data and "y" in self._data:
            self.plot(self._data["x"], self._data["y"], **self._plt_kwargs)

    def add_line(self, x, y, color: str = "r", gid: str = "gid", zorder: int = 5, repaint: bool = True):
        """Add line."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_add(x, y, color=color, gid=gid, zorder=zorder)
            self.figure.repaint(repaint)

    def add_centroids(self, x: np.ndarray, y: np.ndarray, gid: str, repaint: bool = True):
        """Add centroid markers."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_centroid(x, y, gid=gid)
            self.figure.repaint(repaint)

    def remove_line(self, gid: str, repaint: bool = True):
        """Remove line."""
        with QMutexLocker(MUTEX):
            try:
                self.figure.plot_1d_remove(gid)
            except AttributeError:
                pass
            self.figure.repaint(repaint)

    def update_line_color(self, gid: str, color: str, repaint: bool = True):
        """Update line color."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_color(color, gid)
            self.figure.repaint(repaint)

    def update_line_width(self, width: float = 1.0, gid: str | None = None, repaint: bool = True):
        """Update line width."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_width(width, gid)
            self.figure.repaint(repaint)

    def update_line_style(self, style: str = "solid", gid: str | None = None, repaint: bool = True):
        """Update line style."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_style(style, gid)
            self.figure.repaint(repaint)

    def update_line_alpha(self, alpha: float = 1.0, gid: str | None = None, repaint: bool = True):
        """Update line alpha."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_alpha(alpha, gid)
            self.figure.repaint(repaint)

    def _update(self):
        """Update plot with cached data."""
        with QMutexLocker(MUTEX):
            if "x" in self._data and "y" in self._data:
                self.update(self._data["x"], self._data["y"], **self._plt_kwargs)


class ViewVispyLine(_BaseVispyView):
    """VisPy-backed line view."""

    PLOT_TYPE = "line"

    def _create_figure(self, parent, *args, **kwargs):
        return PlotLine(parent, *args, **kwargs)

    def plot(self, x, y, repaint: bool = True, **kwargs):
        """Plot line data."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except (AttributeError, OverflowError):
                self.figure.clear()
                self.figure.plot_1d(x, y, **kwargs)
                self.figure.repaint(repaint)
                self._cache_xy(x, y, **kwargs)

    def update(self, x, y, repaint: bool = True, **kwargs):
        """Update line data without clearing the figure."""
        self.set_labels(**kwargs)
        self.figure.plot_1d_update_data(x, y, **kwargs)
        self.figure.repaint(repaint)
        self._cache_xy(x, y, **kwargs)


class ViewVispyScatter(_BaseVispyView):
    """VisPy-backed scatter view."""

    PLOT_TYPE = "scatter"

    def _create_figure(self, parent, *args, **kwargs):
        return PlotScatter(parent, *args, facecolor="black", **kwargs)

    def plot(self, x, y, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Plot scatter data."""
        del forced_kwargs
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except (AttributeError, OverflowError):
                self.figure.clear()
                self.figure.plot_scatter(
                    x,
                    y,
                    x_label=self.x_label,
                    y_label=self.y_label,
                    callbacks=self._callbacks,
                    **kwargs,
                )
                self.figure.repaint(repaint)
                self._cache_xy(x, y, **kwargs)

    def update(self, x, y, repaint: bool = True, **kwargs):
        """Update scatter data."""
        self.set_labels(**kwargs)
        self.figure.update_scatter(x, y, **kwargs)
        self.figure.repaint(repaint)
        self._cache_xy(x, y, **kwargs)
