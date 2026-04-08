"""PyQtGraph-backed plotting views."""

from __future__ import annotations

import typing as ty
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from koyo.secret import get_short_hash
from koyo.system import is_installed
from qtpy.QtCore import QMutexLocker, QRectF
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QGraphicsItem, QGraphicsRectItem, QWidget

from qtextraplot.utils.views_base import MUTEX, ViewBase

if ty.TYPE_CHECKING:
    from qtpy.QtGui import QPen

if not is_installed("pyqtgraph"):
    raise ImportError("please install pyqtgraph using 'pip install pyqtgraph'")  # noqa: TRY003
import pyqtgraph as pg


def _mk_pen(color: ty.Any = "w", width: float = 1.0, style: str | None = None) -> QPen:
    """Create a pyqtgraph pen with optional line style."""
    style_map = {
        "solid": None,
        "dashed": "DashLine",
        "dash": "DashLine",
        "dotted": "DotLine",
        "dot": "DotLine",
        "dashdot": "DashDotLine",
    }
    kwargs: dict[str, ty.Any] = {"color": color, "width": width}
    if style:
        pen_style = style_map.get(style.lower())
        if pen_style:
            kwargs["style"] = getattr(pg.QtCore.Qt.PenStyle, pen_style)
    return pg.mkPen(**kwargs)


def _mk_brush(color: ty.Any = None):
    """Create a pyqtgraph brush."""
    if color is None:
        return pg.mkBrush(0, 0, 0, 0)
    return pg.mkBrush(color)


def _coerce_image(image: np.ndarray) -> np.ndarray:
    """Prepare image data for pyqtgraph display."""
    image = np.asarray(image)
    if image.ndim == 3 and image.shape[2] in (3, 4):
        return np.swapaxes(image, 0, 1)
    return image.T


@dataclass
class RectPatchAdapter:
    """Adapter that gives a rectangle item an MPL-like update surface."""

    name: str | None
    item: QGraphicsRectItem

    def _rect(self) -> QRectF:
        return self.item.rect()

    def set_facecolor(self, color: ty.Any) -> None:
        self.item.setBrush(_mk_brush(color))

    def set_xy(self, xy: tuple[float, float]) -> None:
        rect = self._rect()
        self.item.setRect(QRectF(xy[0], xy[1], rect.width(), rect.height()))

    def set_x(self, x: float) -> None:
        rect = self._rect()
        self.item.setRect(QRectF(x, rect.y(), rect.width(), rect.height()))

    def set_y(self, y: float) -> None:
        rect = self._rect()
        self.item.setRect(QRectF(rect.x(), y, rect.width(), rect.height()))

    def set_width(self, width: float) -> None:
        rect = self._rect()
        self.item.setRect(QRectF(rect.x(), rect.y(), width, rect.height()))

    def set_height(self, height: float) -> None:
        rect = self._rect()
        self.item.setRect(QRectF(rect.x(), rect.y(), rect.width(), height))


class PyQtGraphCanvas(pg.PlotWidget):
    """Reusable pyqtgraph canvas with qtextraplot-style methods."""

    def __init__(self, parent: QWidget | None = None, *, title: str = "", x_label: str = "", y_label: str = ""):
        super().__init__(parent=parent, background=None)
        self._ax = self.getPlotItem()
        self._title = title
        self._base_gid = "__base__"
        self._scatter_gid = "__scatter__"
        self._image_gid = "__image__"
        self._plot_items: dict[str, ty.Any] = {}
        self._annotation_items: dict[str, ty.Any] = {}
        self._patch_items: dict[str, RectPatchAdapter] = {}
        self.showGrid(x=True, y=True, alpha=0.15)
        self.setMenuEnabled(False)
        self.setClipToView(True)
        self._ax.setDownsampling(auto=True, mode="peak")
        self._ax.setTitle(title)
        self._ax.setLabel("bottom", x_label)
        self._ax.setLabel("left", y_label)

    @property
    def x_axis(self):
        """Compatibility shim for code that expects axis objects."""
        return self._ax.getAxis("bottom")

    @property
    def y_axis(self):
        """Compatibility shim for code that expects axis objects."""
        return self._ax.getAxis("left")

    def repaint(self, repaint: bool = True) -> None:
        """Refresh the widget."""
        if repaint:
            self.getViewBox().update()
            self.update()

    def clear(self) -> None:
        """Remove all data and annotations."""
        super().clear()
        self._plot_items.clear()
        self._annotation_items.clear()
        self._patch_items.clear()
        self._ax.setTitle(self._title)

    def copy_to_clipboard(self) -> None:
        """Copy the current canvas to the clipboard."""
        QApplication.clipboard().setPixmap(self.grab())

    def savefig(self, path: str | Path, **_: ty.Any) -> None:
        """Save a raster snapshot of the widget."""
        self.grab().save(str(path))

    def tight(self, _tight: bool = True) -> None:
        """Compatibility no-op."""

    def setup_interactivity(self, **_: ty.Any) -> None:
        """Compatibility no-op."""

    def set_plot_title(self, title: str, **_: ty.Any) -> None:
        """Set plot title."""
        self._title = title
        self._ax.setTitle(title)

    def _add_or_replace_item(self, registry: dict[str, ty.Any], gid: str, item: ty.Any) -> ty.Any:
        existing = registry.pop(gid, None)
        if isinstance(existing, list):
            for child in existing:
                self._ax.removeItem(child)
        elif existing is not None:
            self._ax.removeItem(existing)
        registry[gid] = item
        self._ax.addItem(item)
        return item

    def remove_gid(self, gid: str) -> None:
        """Remove any item registered under the given gid."""
        item = self._plot_items.pop(gid, None)
        if item is not None:
            self._ax.removeItem(item)
        item = self._annotation_items.pop(gid, None)
        if isinstance(item, list):
            for child in item:
                self._ax.removeItem(child)
        elif item is not None:
            self._ax.removeItem(item)
        patch = self._patch_items.pop(gid, None)
        if patch is not None:
            self._ax.removeItem(patch.item)

    def plot_1d(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        gid: str | None = None,
        color: ty.Any = "w",
        width: float = 1.0,
        **kwargs: ty.Any,
    ):
        """Plot a primary line."""
        gid = gid or self._base_gid
        item = pg.PlotDataItem(x=np.asarray(x), y=np.asarray(y), pen=_mk_pen(color, width))
        return self._add_or_replace_item(self._plot_items, gid, item)

    def plot_1d_update_data(
        self,
        x: np.ndarray,
        y: np.ndarray,
        _x_label: str | None = None,
        _y_label: str | None = None,
        *,
        gid: str | None = None,
        color: ty.Any | None = None,
        width: float | None = None,
        **kwargs: ty.Any,
    ) -> None:
        """Update an existing line."""
        gid = gid or self._base_gid
        item = self._plot_items.get(gid)
        if item is None:
            raise AttributeError(f"No line registered for gid={gid!r}")  # noqa: TRY003
        item.setData(np.asarray(x), np.asarray(y))
        if color is not None or width is not None:
            pen = item.opts.get("pen", _mk_pen())
            width_value = width if width is not None else pen.widthF()
            color_value = color if color is not None else pen.color()
            item.setPen(_mk_pen(color_value, width_value))

    def plot_1d_add(
        self,
        x: np.ndarray,
        y: np.ndarray,
        color: ty.Any = "w",
        gid: str = "line",
        width: float = 1.0,
        zorder: int = 0,
    ):
        """Add another line to the plot."""
        item = pg.PlotDataItem(x=np.asarray(x), y=np.asarray(y), pen=_mk_pen(color, width))
        item.setZValue(zorder)
        return self._add_or_replace_item(self._plot_items, gid, item)

    def plot_1d_remove(self, gid: str) -> None:
        """Remove a line by gid."""
        self.remove_gid(gid)

    def plot_1d_update_color(self, gid: str, color: ty.Any) -> None:
        """Update line color."""
        item = self._plot_items[gid]
        pen = item.opts.get("pen", _mk_pen())
        item.setPen(_mk_pen(color, pen.widthF()))

    def plot_1d_update_line_width(self, line_width: float, gid: str | None = None) -> None:
        """Update line width."""
        item = self._plot_items[gid or self._base_gid]
        pen = item.opts.get("pen", _mk_pen())
        item.setPen(_mk_pen(pen.color(), line_width))

    def plot_1d_update_line_style(self, line_style: str, gid: str | None = None) -> None:
        """Update line style."""
        item = self._plot_items[gid or self._base_gid]
        pen = item.opts.get("pen", _mk_pen())
        item.setPen(_mk_pen(pen.color(), pen.widthF(), style=line_style))

    def plot_1d_update_line_alpha(self, line_alpha: float, gid: str | None = None) -> None:
        """Update line alpha."""
        item = self._plot_items[gid or self._base_gid]
        pen = item.opts.get("pen", _mk_pen())
        color = QColor(pen.color())
        color.setAlphaF(max(0.0, min(1.0, line_alpha)))
        item.setPen(_mk_pen(color, pen.widthF()))

    def plot_1d_centroid(self, x: np.ndarray, y: np.ndarray, gid: str = "centroids", **kwargs: ty.Any):
        """Add centroid markers."""
        item = pg.ScatterPlotItem(
            x=np.asarray(x),
            y=np.asarray(y),
            pen=_mk_pen(kwargs.get("color", "w"), kwargs.get("width", 1.0)),
            brush=_mk_brush(kwargs.get("color", "w")),
            size=kwargs.get("size", kwargs.get("width", 8)),
        )
        return self._add_or_replace_item(self._plot_items, gid, item)

    def plot_scatter(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        gid: str | None = None,
        color: ty.Any = "w",
        size: float = 5,
        marker: str = "o",
        **kwargs: ty.Any,
    ):
        """Plot scatter data."""
        gid = gid or self._scatter_gid
        item = pg.ScatterPlotItem(
            x=np.asarray(x),
            y=np.asarray(y),
            pen=_mk_pen(color, kwargs.get("width", 1.0)),
            brush=_mk_brush(color),
            size=size,
            symbol=marker,
        )
        return self._add_or_replace_item(self._plot_items, gid, item)

    def update_scatter(self, x: np.ndarray, y: np.ndarray, *, gid: str | None = None, **kwargs: ty.Any) -> None:
        """Update scatter data."""
        gid = gid or self._scatter_gid
        item = self._plot_items.get(gid)
        if item is None:
            raise AttributeError(f"No scatter registered for gid={gid!r}")  # noqa: TRY003
        item.setData(x=np.asarray(x), y=np.asarray(y), size=kwargs.get("size", item.opts.get("size", 5)))

    def imshow(self, image: np.ndarray, *, gid: str | None = None, auto_levels: bool = True, **kwargs: ty.Any):
        """Display image data."""
        gid = gid or self._image_gid
        item = self._plot_items.get(gid)
        if not isinstance(item, pg.ImageItem):
            item = pg.ImageItem()
            item.setZValue(kwargs.get("zorder", -100))
            self._add_or_replace_item(self._plot_items, gid, item)
        item.setImage(_coerce_image(image), autoLevels=auto_levels)
        item.setOpacity(kwargs.get("opacity", 1.0))
        if "levels" in kwargs and kwargs["levels"] is not None:
            item.setLevels(kwargs["levels"])
        if "rect" in kwargs and kwargs["rect"] is not None:
            item.setRect(kwargs["rect"])
        self.getViewBox().setAspectLocked(kwargs.get("aspect", "equal") == "equal")
        self._ax.enableAutoRange()
        return item

    def update_image(self, image: np.ndarray, **kwargs: ty.Any) -> None:
        """Update image data."""
        self.imshow(image, **kwargs)

    def plot_add_infline(
        self,
        *,
        pos: float,
        angle: float,
        gid: str,
        color: ty.Any = "w",
        width: float = 1.0,
        movable: bool = False,
        **kwargs: ty.Any,
    ):
        """Add an infinite line annotation."""
        item = pg.InfiniteLine(pos=pos, angle=angle, movable=movable, pen=_mk_pen(color, width), **kwargs)
        return self._add_or_replace_item(self._annotation_items, gid, item)

    def plot_add_vline(self, xpos: float = 0, gid: str = "ax_vline", **kwargs: ty.Any):
        """Add a vertical line annotation."""
        return self.plot_add_infline(pos=xpos, angle=90, gid=gid, **kwargs)

    def plot_add_hline(self, ypos: float = 0, gid: str = "ax_hline", **kwargs: ty.Any):
        """Add a horizontal line annotation."""
        return self.plot_add_infline(pos=ypos, angle=0, gid=gid, **kwargs)

    def plot_add_varrow(self, xpos: float = 0, gid: str = "ax_varrow", color: ty.Any = "w"):
        """Add a vertical marker line."""
        line = self.plot_add_vline(xpos=xpos, gid=gid, color=color)
        line.addMarker("^", position=0.95)
        return line

    def plot_add_vlines(self, vlines: ty.Iterable[float], gid: str = "vlines", color: ty.Any = "w"):
        """Add multiple vertical lines."""
        items = [pg.InfiniteLine(pos=x, angle=90, movable=False, pen=_mk_pen(color, 1.0)) for x in vlines]
        for item in self._annotation_items.pop(gid, []):
            self._ax.removeItem(item)
        self._annotation_items[gid] = items
        for item in items:
            self._ax.addItem(item)
        return items

    def plot_remove_line(self, gid: str) -> None:
        """Remove an annotation line."""
        item = self._annotation_items.pop(gid, None)
        if isinstance(item, list):
            for child in item:
                self._ax.removeItem(child)
            return
        if item is not None:
            self._ax.removeItem(item)

    def plot_add_patch(
        self,
        x: float,
        y: float,
        width: float,
        height: float | None = None,
        *,
        obj_name: str | None = None,
        color: ty.Any = "r",
        pickable: bool = True,
    ) -> RectPatchAdapter:
        """Add a rectangular annotation patch."""
        height = width if height is None else height
        item = QGraphicsRectItem(QRectF(x, y, width, height))
        item.setPen(_mk_pen(color, 1.0))
        item.setBrush(_mk_brush(color))
        if pickable:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        adapter = RectPatchAdapter(obj_name, item)
        if obj_name:
            existing = self._patch_items.pop(obj_name, None)
            if existing is not None:
                self._ax.removeItem(existing.item)
            self._patch_items[obj_name] = adapter
        self._ax.addItem(item)
        return adapter

    def get_existing_patch(self, obj_name: str) -> RectPatchAdapter | None:
        """Get an existing patch."""
        return self._patch_items.get(obj_name)

    def plot_remove_patches(self, start_with: str | None = None, _repaint: bool = True) -> None:
        """Remove patches, optionally filtered by prefix."""
        for name in list(self._patch_items):
            if start_with is None or name.startswith(start_with):
                patch = self._patch_items.pop(name)
                self._ax.removeItem(patch.item)

    def get_xlim(self) -> tuple[float, float]:
        """Get x-axis limits."""
        return tuple(self._ax.viewRange()[0])

    def get_current_xlim(self) -> tuple[float, float]:
        """Get current x-axis limits."""
        return self.get_xlim()

    def get_ylim(self) -> tuple[float, float]:
        """Get y-axis limits."""
        return tuple(self._ax.viewRange()[1])

    def get_current_ylim(self) -> tuple[float, float]:
        """Get current y-axis limits."""
        return self.get_ylim()

    def get_xy_limits(self) -> tuple[float, float, float, float]:
        """Get current plot limits."""
        xmin, xmax = self.get_xlim()
        ymin, ymax = self.get_ylim()
        return xmin, xmax, ymin, ymax

    def get_xy_zoom(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get current zoom state."""
        return self.get_xlim(), self.get_ylim()

    def on_zoom_x_axis(self, x_min: float, x_max: float) -> None:
        """Set x-axis range."""
        self.setXRange(x_min, x_max, padding=0)

    def on_zoom_y_axis(self, y_min: float, y_max: float) -> None:
        """Set y-axis range."""
        self.setYRange(y_min, y_max, padding=0)

    def on_set_x_axis(self, x_min: float, x_max: float) -> None:
        """Alias for x-axis zoom."""
        self.on_zoom_x_axis(x_min, x_max)

    def on_zoom_xy_axis(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        """Set x/y axis ranges."""
        self.setXRange(x_min, x_max, padding=0)
        self.setYRange(y_min, y_max, padding=0)

    def reset_limits(self, reset_x: bool = True, reset_y: bool = True, repaint: bool = True) -> None:
        """Reset view to fit all items."""
        if reset_x and reset_y:
            self.enableAutoRange()
        elif reset_x:
            self.enableAutoRange(axis=pg.ViewBox.XAxis)
        elif reset_y:
            self.enableAutoRange(axis=pg.ViewBox.YAxis)
        self.repaint(repaint)

    def on_reset_zoom(self) -> None:
        """Reset view to data bounds."""
        self.enableAutoRange()

    def set_xy_line_limits(self, reset_x: bool = True, reset_y: bool = True) -> None:
        """Compatibility alias used by existing views."""
        self.reset_limits(reset_x=reset_x, reset_y=reset_y, repaint=False)


class _BasePyQtGraphView(ViewBase):
    """Common base class for pyqtgraph-backed views."""

    def __init__(self, parent: QWidget, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(parent, *args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.figure = PyQtGraphCanvas(parent, title=self.title, x_label=self.x_label or "", y_label=self.y_label or "")
        self.widget = self.figure

    def unregister(self):
        """Compatibility hook."""

    @property
    def x_label(self):
        """Return x-axis label."""
        return self._x_label

    @x_label.setter
    def x_label(self, value):
        if value == self._x_label:
            return
        self._x_label = value
        self.figure._ax.setLabel("bottom", value or "")
        self._update()

    @property
    def y_label(self):
        """Return y-axis label."""
        return self._y_label

    @y_label.setter
    def y_label(self, value):
        if value == self._y_label:
            return
        self._y_label = value
        self.figure._ax.setLabel("left", value or "")
        self._update()

    def _sync_labels(self) -> None:
        """Push cached labels into the pyqtgraph axes."""
        self.figure._ax.setLabel("bottom", self._x_label or "")
        self.figure._ax.setLabel("left", self._y_label or "")

    def figure_update(self, add_zoom: bool = True, repaint: bool = True, tight: bool = True):
        """Update and repaint figure."""
        self.figure.tight(tight)
        if add_zoom:
            self.figure.reset_limits(repaint=False)
        self.figure.repaint(repaint)

    def set_title(self, title, repaint: bool = True, tight: bool = True, **kwargs):
        """Set title on the plot."""
        self.figure.set_plot_title(title, **kwargs)
        self.figure.tight(tight)
        self.figure.repaint(repaint)

    def add_line(
        self,
        x,
        y,
        color: str = "r",
        gid: str = "gid",
        zorder: int = 5,
        repaint: bool = True,
        label: str = "",
    ):
        """Add line."""
        del label
        self.figure.plot_1d_add(x, y, color=color, gid=gid, zorder=zorder)
        self.figure.set_xy_line_limits()
        self.figure.repaint(repaint)

    def add_centroids(self, x: np.ndarray, y: np.ndarray, gid: str, repaint: bool = True):
        """Add centroid markers."""
        self.figure.plot_1d_centroid(x, y, gid=gid)
        self.figure.repaint(repaint)

    def remove_gid(self, gid: str, repaint: bool = True):
        """Remove any gid."""
        self.figure.remove_gid(gid)
        self.figure.repaint(repaint)

    def remove_line(self, gid: str, repaint: bool = True):
        """Remove line."""
        self.figure.plot_1d_remove(gid)
        self.figure.set_xy_line_limits()
        self.figure.repaint(repaint)

    def update_line_color(self, gid: str, color: ty.Union[str, np.ndarray], repaint: bool = True):
        """Update line color."""
        self.figure.plot_1d_update_color(gid, color)
        self.figure.repaint(repaint)

    def update_line_width(self, width: float = 1.0, gid: str | None = None, repaint: bool = True):
        """Update line width."""
        self.figure.plot_1d_update_line_width(width, gid)
        self.figure.repaint(repaint)

    def update_line_style(self, style: str = "solid", gid: str | None = None, repaint: bool = True):
        """Update line style."""
        self.figure.plot_1d_update_line_style(style, gid)
        self.figure.repaint(repaint)

    def update_line_alpha(self, alpha: float = 1.0, gid: str | None = None, repaint: bool = True):
        """Update line alpha."""
        self.figure.plot_1d_update_line_alpha(alpha, gid)
        self.figure.repaint(repaint)

    def _update(self):
        """Update plot with current data."""
        if "x" in self._data and "y" in self._data:
            self.update(self._data["x"], self._data["y"], **self._plt_kwargs)


class ViewPyQtGraphCanvas(_BasePyQtGraphView):
    """Universal PyQtGraph view that can mix lines, scatter, and images."""

    PLOT_TYPE = "mixed"

    def __init__(self, parent: QWidget, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(parent, *args, **kwargs)
        self._items_state: dict[str, dict[str, ty.Any]] = {}

    def _store_item_state(self, gid: str, kind: str, **kwargs: ty.Any) -> None:
        """Persist item state so the canvas can be reconstructed after reset."""
        self._items_state[gid] = {"kind": kind, **kwargs}

    def _drop_item_state(self, gid: str) -> None:
        """Remove stored state for an item."""
        self._items_state.pop(gid, None)

    def _rebuild_items(self) -> None:
        """Recreate all stored items."""
        states = list(self._items_state.items())
        self.figure.clear()
        for gid, state in states:
            kind = state["kind"]
            params = {key: value for key, value in state.items() if key != "kind"}
            if kind == "line":
                self.figure.plot_1d_add(gid=gid, **params)
            elif kind == "scatter":
                self.figure.plot_scatter(gid=gid, **params)
            elif kind == "image":
                self.figure.imshow(gid=gid, **params)
            elif kind == "centroids":
                self.figure.plot_1d_centroid(gid=gid, **params)
            elif kind == "vline":
                self.figure.plot_add_vline(gid=gid, **params)
            elif kind == "hline":
                self.figure.plot_add_hline(gid=gid, **params)
            elif kind == "infline":
                self.figure.plot_add_infline(gid=gid, **params)

    def plot(
        self,
        x,
        y,
        repaint: bool = True,
        forced_kwargs: dict | None = None,
        gid: str = "__base__",
        **kwargs: ty.Any,
    ) -> None:
        """Plot or replace a line item without clearing other items."""
        del forced_kwargs
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            plot_kwargs = dict(kwargs)
            color = plot_kwargs.pop("color", "w")
            width = plot_kwargs.pop("width", 1.0)
            zorder = plot_kwargs.pop("zorder", 0)
            x_array = np.asarray(x)
            y_array = np.asarray(y)
            self.figure.plot_1d_add(x_array, y_array, gid=gid, color=color, width=width, zorder=zorder)
            self.figure.set_xy_line_limits()
            self.figure.repaint(repaint)
            self._store_item_state(
                gid,
                "line",
                x=x_array,
                y=y_array,
                color=color,
                width=width,
                zorder=zorder,
            )

    def scatter(
        self,
        x,
        y,
        repaint: bool = True,
        gid: str = "__scatter__",
        **kwargs: ty.Any,
    ) -> None:
        """Plot or replace a scatter item without clearing other items."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            plot_kwargs = dict(kwargs)
            color = plot_kwargs.pop("color", "w")
            size = plot_kwargs.pop("size", 5)
            marker = plot_kwargs.pop("marker", "o")
            width = plot_kwargs.pop("width", 1.0)
            x_array = np.asarray(x)
            y_array = np.asarray(y)
            self.figure.plot_scatter(x_array, y_array, gid=gid, color=color, size=size, marker=marker, width=width)
            self.figure.repaint(repaint)
            self._store_item_state(
                gid,
                "scatter",
                x=x_array,
                y=y_array,
                color=color,
                size=size,
                marker=marker,
                width=width,
            )

    def imshow(self, image: np.ndarray, repaint: bool = True, gid: str = "__image__", **kwargs: ty.Any) -> None:
        """Plot or replace an image item without clearing other items."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            plot_kwargs = dict(kwargs)
            image_array = np.asarray(image)
            self.figure.imshow(image_array, gid=gid, **plot_kwargs)
            self.figure.repaint(repaint)
            self._store_item_state(gid, "image", image=image_array, **plot_kwargs)

    def add_line(
        self,
        x,
        y,
        color: str = "r",
        gid: str = "gid",
        zorder: int = 5,
        repaint: bool = True,
        label: str = "",
    ):
        """Add a secondary line."""
        del label
        self.plot(x, y, repaint=repaint, gid=gid, color=color, zorder=zorder)

    def add_centroids(self, x: np.ndarray, y: np.ndarray, gid: str, repaint: bool = True):
        """Add centroid markers."""
        with QMutexLocker(MUTEX):
            x_array = np.asarray(x)
            y_array = np.asarray(y)
            self.figure.plot_1d_centroid(x_array, y_array, gid=gid)
            self.figure.repaint(repaint)
            self._store_item_state(gid, "centroids", x=x_array, y=y_array)

    def add_vline(self, xpos: float = 0, gid: str = "ax_vline", repaint: bool = True, **kwargs: ty.Any):
        """Add a vertical annotation."""
        with QMutexLocker(MUTEX):
            self.figure.remove_gid(gid)
            self.figure.plot_add_vline(xpos=xpos, gid=gid, **kwargs)
            self.figure.repaint(repaint)
            self._store_item_state(gid, "vline", xpos=xpos, **kwargs)

    def add_hline(self, ypos: float = 0, gid: str = "ax_hline", repaint: bool = True, **kwargs: ty.Any):
        """Add a horizontal annotation."""
        with QMutexLocker(MUTEX):
            self.figure.remove_gid(gid)
            self.figure.plot_add_hline(ypos=ypos, gid=gid, **kwargs)
            self.figure.repaint(repaint)
            self._store_item_state(gid, "hline", ypos=ypos, **kwargs)

    def add_infline(
        self,
        *,
        pos: float,
        angle: float,
        gid: str = "infline",
        repaint: bool = True,
        **kwargs: ty.Any,
    ) -> None:
        """Add a generic infinite line annotation."""
        with QMutexLocker(MUTEX):
            self.figure.remove_gid(gid)
            self.figure.plot_add_infline(pos=pos, angle=angle, gid=gid, **kwargs)
            self.figure.repaint(repaint)
            self._store_item_state(gid, "infline", pos=pos, angle=angle, **kwargs)

    def remove_gid(self, gid: str, repaint: bool = True):
        """Remove any plotted item or annotation."""
        self.figure.remove_gid(gid)
        self._drop_item_state(gid)
        self.figure.repaint(repaint)

    def clear(self) -> None:
        """Clear the canvas and stored item state."""
        self._items_state.clear()
        super().clear()

    def reset(self):
        """Rebuild the full mixed canvas from stored item state."""
        self._rebuild_items()
        self.figure.repaint(True)


class ViewPyQtGraphLine(_BasePyQtGraphView):
    """PyQtGraph line view."""

    PLOT_TYPE = "line"

    def plot(self, x, y, repaint: bool = True, forced_kwargs: dict | None = None, **kwargs: ty.Any) -> None:
        """Plot a line."""
        del forced_kwargs
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except AttributeError:
                plot_kwargs = dict(kwargs)
                self.figure.clear()
                self.figure.plot_1d(
                    x,
                    y,
                    color=plot_kwargs.pop("color", "w"),
                    width=plot_kwargs.pop("width", 1.0),
                    **plot_kwargs,
                )
                self.figure.repaint(repaint)
                self._data.update(x=np.asarray(x), y=np.asarray(y))
                self._plt_kwargs = dict(kwargs)

    def update(self, x, y, repaint: bool = True, **kwargs: ty.Any) -> None:
        """Update line data."""
        self.set_labels(**kwargs)
        self._sync_labels()
        update_kwargs = dict(kwargs)
        self.figure.plot_1d_update_data(
            x,
            y,
            color=update_kwargs.pop("color", None),
            width=update_kwargs.pop("width", None),
            **update_kwargs,
        )
        self.figure.set_xy_line_limits(reset_y=True)
        self.figure.repaint(repaint)
        self._data.update(x=np.asarray(x), y=np.asarray(y))
        self._plt_kwargs = dict(kwargs)

    def reset(self):
        """Reset the view from cached data."""
        self.light_clear()
        if "x" in self._data and "y" in self._data:
            self.plot(self._data["x"], self._data["y"], **self._plt_kwargs)

    def imshow(self, image: np.ndarray, axis: bool = False, **kwargs: ty.Any) -> None:
        """Display an image in the same canvas."""
        del axis
        self.figure.clear()
        self.figure.imshow(image, **kwargs)
        self.figure.repaint()


class ViewPyQtGraphScatter(_BasePyQtGraphView):
    """PyQtGraph scatter view."""

    PLOT_TYPE = "scatter"

    def plot(self, x, y, repaint: bool = True, forced_kwargs: dict | None = None, **kwargs: ty.Any) -> None:
        """Plot scatter data."""
        del forced_kwargs
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except AttributeError:
                plot_kwargs = dict(kwargs)
                self.figure.clear()
                self.figure.plot_scatter(x, y, **plot_kwargs)
                self.figure.repaint(repaint)
                self._data.update(x=np.asarray(x), y=np.asarray(y))
                self._plt_kwargs = dict(kwargs)

    def update(self, x, y, repaint: bool = True, **kwargs: ty.Any) -> None:
        """Update scatter data."""
        self.set_labels(**kwargs)
        self._sync_labels()
        self.figure.update_scatter(x, y, **kwargs)
        self.figure.repaint(repaint)
        self._data.update(x=np.asarray(x), y=np.asarray(y))
        self._plt_kwargs = dict(kwargs)


class ViewPyQtGraphImage(_BasePyQtGraphView):
    """PyQtGraph image view."""

    PLOT_TYPE = "image"

    def plot(
        self,
        image: np.ndarray,
        repaint: bool = True,
        forced_kwargs: dict | None = None,
        **kwargs: ty.Any,
    ) -> None:
        """Plot image data."""
        del forced_kwargs
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            self.figure.imshow(image, **kwargs)
            self.figure.repaint(repaint)
            self._data.update(image=np.asarray(image))
            self._plt_kwargs = dict(kwargs)

    def imshow(self, image: np.ndarray, axis: bool = False, **kwargs: ty.Any) -> None:
        """Display image data."""
        del axis
        self.plot(image, **kwargs)

    def update(self, image: np.ndarray, repaint: bool = True, **kwargs: ty.Any) -> None:
        """Update image data."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)
            self._sync_labels()
            self.figure.update_image(image, **kwargs)
            self.figure.repaint(repaint)
            self._data.update(image=np.asarray(image))
            self._plt_kwargs = dict(kwargs)

    def reset(self):
        """Reset the image from cached data."""
        self.light_clear()
        if "image" in self._data:
            self.plot(self._data["image"], **self._plt_kwargs)
