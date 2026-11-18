"""Line viewer."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
from koyo.secret import get_short_hash
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event
from napari_plot.layers import (
    Band,
    Bar,
    Centroids,
    ErrorBar,
    InfLine,
    Line,
    MultiLine,
    Rectangles,
    Region,
    Scatter,
    Text,
    Vectors,
)
from napari_plot.layers.base import update_layer_attributes
from napari_plot.viewer import ViewerModel as Viewer
from qtpy.QtCore import QMutex
from qtpy.QtWidgets import QWidget

from qtextraplot._napari._utilities import get_font_for_os
from qtextraplot._napari._wrapper import ViewerBase
from qtextraplot._napari.line._vispy.overrides.axis import tick_formatter
from qtextraplot._napari.line.config import Config
from qtextraplot._napari.line.qt_viewer import QtViewer, as_array
from qtextraplot.config import CANVAS

if ty.TYPE_CHECKING:
    from napari_plot.layers import Areas

MUTEX = QMutex()

LINE_NAME, CENTROID_NAME, SCATTER_NAME, REGION_NAME = "Line", "Centroids", "Scatter", "Region"
BAR_NAME, BAND_NAME, ERROR_BAR_NAME, TEXT_NAME = "Bar", "Band", "Error bars", "Text"
RECTANGLES_NAME, VECTORS_NAME, MULTI_LINE_NAME, AREAS_NAME = "Rectangles", "Vectors", "MultiLine", "Areas"
EXTRACT_NAME = "Extract mask"


class NapariLineView(ViewerBase):
    """Napari-based image viewer."""

    # define plot type
    PLOT_TYPE = "line"

    _instances: ty.ClassVar[list] = []

    def __init__(
        self,
        parent: QWidget | None = None,
        x_label: str = "",
        y_label: str = "",
        lock_to_bottom: bool = False,
        tool: str = "auto",
        extent_mode: str = "restricted",
        **kwargs: ty.Any,
    ):
        self.parent = parent
        self.main_parent = kwargs.pop("main_parent", None)
        self.PLOT_ID = get_short_hash()

        # Configuration file
        self.config = Config()

        # create an instance of viewer
        self.viewer: Viewer = Viewer()
        self.viewer.axis.y_tick_formatter = tick_formatter
        self.viewer.drag_tool.active = tool
        self.viewer.camera.extent_mode = extent_mode
        self.viewer.axis.x_label = x_label
        self.viewer.axis.y_label = y_label
        self.viewer.axis.label_size = 8
        self.viewer.axis.tick_size = 6
        if lock_to_bottom:
            self.viewer.camera.axis_mode = "lock_to_bottom"
        else:
            self.viewer.camera.axis_mode = "all"

        # create instance of qt widget
        self.widget = QtViewer(
            self.viewer,
            parent=parent,
            disable_controls=kwargs.pop("disable_controls", False),
            add_toolbars=kwargs.pop("add_toolbars", True),
            allow_extraction=kwargs.pop("allow_extraction", True),
            allow_tools=kwargs.pop("allow_tools", False),
            allow_legend=kwargs.pop("allow_legend", True),
            connect_theme=kwargs.pop("connect_theme", True),
        )
        font = get_font_for_os()
        self.widget.x_axis.node.axis._text.face = font
        self.widget.x_axis.node.axis._axis_label_vis.face = font
        self.widget.y_axis.node.axis._text.face = font
        self.widget.y_axis.node.axis._axis_label_vis.face = font
        self.widget.text_overlay.node.face = font

        # add few layers
        self.line_layer: Line | None = None
        self.region_layer: Region | None = None

        # connect events
        self.viewer.events.clear_canvas.connect(self._clear)
        self.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.viewer.text_overlay.position = "top_right"

        # own instances
        self._instances.append(self)

    def close(self) -> None:
        """Close the view instance."""
        with suppress(ValueError):
            self._instances.remove(self)
        super().close()

    def connect_click(
        self,
        func: ty.Callable[[float, float], None],
        button: int = 1,
        max_move_px: float = 3,
    ) -> ty.Callable:
        """Call `func(x, y)` (in data coordinates) when user clicks in the canvas without dragging.

        Dragging (e.g. box zoom) is not considered a click. Note that a double-click also produces a click, so if both
        actions are needed, the click should be handled with a delay.

        Returns
        -------
        callback : Callable
            Mouse drag callback that can be passed to `disconnect_click`.
        """

        def _on_click(_viewer: Viewer, event: ty.Any) -> ty.Generator[None, None, None]:
            if event.button != button:
                return
            start = np.asarray(event.pos)
            moved = False
            yield
            while event.type == "mouse_move":
                if np.abs(np.asarray(event.pos) - start).max() > max_move_px:
                    moved = True
                yield
            if not moved and event.position is not None:
                y, x = event.position[-2:]
                func(float(x), float(y))

        self.viewer.mouse_drag_callbacks.append(_on_click)
        return _on_click

    def disconnect_click(self, callback: ty.Callable) -> None:
        """Remove callback added by `connect_click`."""
        with suppress(ValueError):
            self.viewer.mouse_drag_callbacks.remove(callback)

    def _update_view(self) -> None:
        self.widget.canvas.native.update()
        xmin, xmax, ymin, ymax = self.viewer.camera.rect
        self.viewer.camera.rect = xmin + 1, xmax, ymin, ymax
        self.viewer.camera.rect = xmin, xmax, ymin, ymax

    def _on_remove_layer(self, evt: Event) -> None:
        """Indicate if layer has been deleted."""
        self._clear_tracked_layer_on_remove(evt.value, "line_layer", "region_layer")

    def _clear(self, _evt: ty.Any = None) -> None:
        """Clear canvas."""
        self._clear_tracked_layers("line_layer", "region_layer")

    def plot(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        name: str = LINE_NAME,
        reset_y: bool = False,
        reset_x: bool = False,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Line:
        """Update data."""
        layer = self.try_reuse(name, Line, reuse=reuse)
        color = kwargs.pop("color", as_array("line", CANVAS))
        if layer:
            update_layer_attributes(layer, False, data=np.c_[x, y], color=color, **kwargs)
        else:
            layer = self.viewer.add_line(np.c_[x, y], name=name, color=color, **kwargs)
        if reset_y:
            self.viewer.reset_y_view()
        if reset_x:
            self.viewer.reset_x_view()
        return layer

    def add_histogram(
        self,
        array: np.ndarray,
        bins: int | np.ndarray = 10,
        rel_width: float = 0.8,
        name: str = "Histogram",
        orientation: str = "vertical",
        face_color: ty.Any = "red",
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Bar:
        """Add histogram of `array` using a Bar layer.

        Parameters
        ----------
        array : np.ndarray
            Values to bin.
        bins : int or np.ndarray
            Number of bins or explicit bin edges, as accepted by `np.histogram`.
        rel_width : float
            Bar width relative to the mean bin width.
        name : str
            Layer name.
        orientation : str
            Bars extend vertically (``"vertical"``) or horizontally (``"horizontal"``).
        face_color : color
            Bar fill color.
        reuse : bool
            Update an existing layer with the same name instead of creating a new one.
        **kwargs
            Extra attributes passed to the Bar layer.
        """
        counts, edges = np.histogram(np.asarray(array), bins=bins)
        centers = (edges[:-1] + edges[1:]) / 2
        width = rel_width * float(np.mean(np.diff(edges))) if len(edges) > 1 else rel_width
        kwargs.setdefault("border_width", 0)
        return self.add_bar(
            centers,
            counts,
            name=name,
            orientation=orientation,
            width=width,
            fill_color=face_color,
            reuse=reuse,
            **kwargs,
        )

    def add_bar(
        self,
        x: ty.Iterable | np.ndarray,
        height: ty.Iterable | np.ndarray,
        name: str = BAR_NAME,
        orientation: str = "vertical",
        width: float = 0.8,
        fill_color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Bar:
        """Add bars at positions `x` with values `height`.

        For ``orientation="horizontal"``, `x` holds the y-axis positions and `height` the bar lengths.
        """
        if fill_color is None:
            fill_color = as_array("line", CANVAS)
        data = np.c_[np.asarray(x, dtype=float), np.asarray(height, dtype=float)]
        attrs = {"data": data, "orientation": orientation, "width": width, "fill_color": fill_color, **kwargs}
        return self._add_or_update(name, Bar, reuse, attrs, lambda: self.viewer.add_bar(name=name, **attrs))

    def fill_between(
        self,
        x: ty.Iterable | np.ndarray,
        y1: ty.Iterable | np.ndarray | float,
        y2: ty.Iterable | np.ndarray | float = 0,
        name: str = BAND_NAME,
        fill_color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Band:
        """Fill the area between `y1` and `y2` on a shared, monotonic `x` grid. NaN bounds leave gaps."""
        if fill_color is None:
            fill_color = as_array("line", CANVAS)
        x = np.asarray(x, dtype=float)
        bounds = [np.broadcast_to(np.asarray(bound, dtype=float), x.shape) for bound in (y1, y2)]
        attrs = {"data": np.column_stack((x, *bounds)), "fill_color": fill_color, **kwargs}
        return self._add_or_update(name, Band, reuse, attrs, lambda: self.viewer.add_band(name=name, **attrs))

    def add_areas(
        self,
        areas: ty.Sequence[np.ndarray],
        name: str = AREAS_NAME,
        orientation: str = "vertical",
        fill_color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Areas:
        """Fill many regions in one layer, each given as an `(N, 3)` array of `(t, lo, hi)` rows.

        With ``orientation="vertical"`` `t` is x and `lo`/`hi` are y values; ``"horizontal"`` swaps them.
        `fill_color` is one color or one per area.
        """
        from napari_plot.layers import Areas  # added after napari-plot 0.4.2

        if fill_color is None:
            fill_color = as_array("line", CANVAS)
        data = [np.asarray(area, dtype=float) for area in areas]
        attrs = {"data": data, "orientation": orientation, "fill_color": fill_color, **kwargs}
        return self._add_or_update(name, Areas, reuse, attrs, lambda: self.viewer.add_areas(name=name, **attrs))

    def add_error_bar(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        xerr: ty.Iterable | np.ndarray | float | None = None,
        yerr: ty.Iterable | np.ndarray | float | None = None,
        name: str = ERROR_BAR_NAME,
        color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> ErrorBar:
        """Add error bars around (`x`, `y`) points.

        Errors can be a scalar, one value per point or a `(2, N)` array of lower and upper offsets.
        """
        if color is None:
            color = as_array("line", CANVAS)
        x = np.asarray(x, dtype=float)
        count = len(x)
        offsets = []
        for error in (xerr, yerr):
            values = np.asarray(np.nan if error is None else error, dtype=float)
            offsets.append(np.broadcast_to(values, (2, count)).T)
        data = np.column_stack((x, np.asarray(y, dtype=float), *offsets))
        attrs = {"data": data, "color": color, **kwargs}
        return self._add_or_update(name, ErrorBar, reuse, attrs, lambda: self.viewer.add_error_bar(name=name, **attrs))

    def add_text(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        text: str | ty.Sequence[str],
        name: str = TEXT_NAME,
        color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Text:
        """Add text labels at (`x`, `y`) data coordinates."""
        if color is None:
            color = as_array("axis", CANVAS)
        data = np.c_[np.atleast_1d(np.asarray(x, dtype=float)), np.atleast_1d(np.asarray(y, dtype=float))]
        attrs = {"data": data, "text": text, "color": color, **kwargs}
        return self._add_or_update(name, Text, reuse, attrs, lambda: self.viewer.add_text(name=name, **attrs))

    def add_rectangles(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        height: ty.Iterable | np.ndarray | float,
        width: ty.Iterable | np.ndarray | float,
        name: str = RECTANGLES_NAME,
        color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Rectangles:
        """Add rectangle outlines centered on (`x`, `y`) with `height` and `width` in data units.

        Extra keyword arguments (e.g. ``text``, ``show_markers``, ``marker_color``) are passed to the layer.
        """
        if color is None:
            color = as_array("line", CANVAS)
        x = np.atleast_1d(np.asarray(x, dtype=float))
        count = len(x)
        data = np.c_[
            x,
            np.atleast_1d(np.asarray(y, dtype=float)),
            np.broadcast_to(np.asarray(height, dtype=float), (count,)),
            np.broadcast_to(np.asarray(width, dtype=float), (count,)),
        ]
        attrs = {"data": data, "outline_color": color, **kwargs}

        def _create() -> Rectangles:
            create_attrs = dict(attrs)
            return self.viewer.add_rectangles(create_attrs.pop("data"), name=name, **create_attrs)

        return self._add_or_update(name, Rectangles, reuse, attrs, _create)

    def add_vectors(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        dx: ty.Iterable | np.ndarray | float,
        dy: ty.Iterable | np.ndarray | float,
        name: str = VECTORS_NAME,
        color: ty.Any = None,
        width: float = 1.0,
        vector_style: str = "arrow",
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Vectors:
        """Add arrows starting at (`x`, `y`) with components (`dx`, `dy`), similar to `matplotlib.quiver`.

        Use ``vector_style="line"`` to draw plain segments (e.g. graph edges) efficiently.
        """
        if color is None:
            color = as_array("line", CANVAS)
        x = np.atleast_1d(np.asarray(x, dtype=float))
        count = len(x)
        start = np.c_[np.atleast_1d(np.asarray(y, dtype=float)), x]  # napari layers use (row, col) = (y, x)
        delta = np.c_[
            np.broadcast_to(np.asarray(dy, dtype=float), (count,)),
            np.broadcast_to(np.asarray(dx, dtype=float), (count,)),
        ]
        attrs = {
            "data": np.stack((start, delta), axis=1),
            "edge_color": color,
            "edge_width": width,
            "vector_style": vector_style,
            **kwargs,
        }
        return self._add_or_update(name, Vectors, reuse, attrs, lambda: self.viewer.add_vectors(name=name, **attrs))

    def add_multi_line(
        self,
        xs: ty.Sequence[np.ndarray] | np.ndarray,
        ys: ty.Sequence[np.ndarray],
        name: str = MULTI_LINE_NAME,
        color: ty.Any = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> MultiLine:
        """Add many lines in a single layer.

        `xs` is either one shared x-array or one x-array per line in `ys`. `color` is one color or one per line.
        """
        if color is None:
            color = as_array("line", CANVAS)
        ys = [np.asarray(y, dtype=float) for y in ys]
        if isinstance(xs, np.ndarray) and xs.ndim == 1:
            xs = [xs] * len(ys)
        data = {"xs": [np.asarray(x, dtype=float) for x in xs], "ys": ys}
        # the layer's color setter requires one RGBA row per line
        colors = transform_color(color)
        if len(colors) == 1:
            colors = np.broadcast_to(colors, (len(ys), 4)).copy()
        attrs = {"data": data, "color": colors, **kwargs}
        return self._add_or_update(
            name,
            MultiLine,
            reuse,
            attrs,
            lambda: self.viewer.add_multi_line(name=name, **attrs),
        )

    def set_legend(self, entries: ty.Any, **kwargs: ty.Any) -> ty.Any:
        """Show a legend built from explicit entries, e.g. ``[{"label": "A", "marker": "disc", "color": "red"}]``.

        Keyword arguments (``position``, ``font_size``, ...) are passed to `napari_plot` ``ViewerModel.set_legend``.
        """
        return self.viewer.set_legend(entries, **kwargs)

    def set_legend_from_layers(self, **kwargs: ty.Any) -> ty.Any:
        """Show a legend with one entry per visible plot layer, kept in sync with the layer list by default."""
        return self.viewer.set_legend_from_layers(**kwargs)

    def clear_legend(self) -> None:
        """Clear and hide the legend."""
        self.viewer.clear_legend()

    def _add_or_update(
        self,
        name: str,
        layer_type: type,
        reuse: bool,
        attrs: dict[str, ty.Any],
        create: ty.Callable[[], ty.Any],
    ) -> ty.Any:
        """Update an existing layer of `layer_type` with `attrs`, or create it if missing or incompatible."""
        layer = self.try_reuse(name, layer_type, reuse=reuse)
        if layer is not None:
            try:
                update_layer_attributes(layer, True, **attrs)
                layer.visible = attrs.get("visible", True)
            except (AttributeError, TypeError, ValueError):
                self.remove_layer(layer)
                layer = None
        if layer is None:
            # a layer with the same name but different type (e.g. legacy Shapes histogram) would clash
            self.remove_layer(name, silent=True)
            layer = create()
        return layer

    def add_scatter(
        self,
        x: ty.Iterable | np.ndarray | None = None,
        y: ty.Iterable | np.ndarray | None = None,
        name: str = SCATTER_NAME,
        xy: np.ndarray | None = None,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Scatter:
        """Add scatter points."""
        layer = self.try_reuse(name, Scatter, reuse=reuse)
        color = kwargs.pop("color", None)
        if color is not None:
            kwargs.setdefault("face_color", color)
            kwargs.setdefault("border_color", color)
        else:
            kwargs.setdefault("face_color", as_array("scatter", CANVAS))
            kwargs.setdefault("border_color", kwargs["face_color"])
        if xy is None and x is not None and y is not None:
            xy = np.c_[y, x]
        if layer:
            try:
                update_layer_attributes(layer, False, data=xy, **kwargs)
                layer.visible = kwargs.get("visible", True)
            except (AttributeError, TypeError, ValueError):
                self.remove_layer(layer)
                layer = None
        if layer is None:
            layer = self.viewer.add_scatter(xy, name=name, **kwargs)
        return layer

    def add_inf_line(
        self,
        position: float,
        orientation: str = "vertical",
        color: tuple | str = (1.0, 0.0, 0.0, 1.0),
        name: str = "InfLine",
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> InfLine:
        """Add inf line."""
        layer = self.try_reuse(name, InfLine, reuse=reuse)
        if layer:
            update_layer_attributes(layer, False, data=[position], color=color, **kwargs)
        else:
            layer = self.viewer.add_inf_line([position], name=name, color=color, orientation=orientation, **kwargs)
        return layer

    def add_centroids(
        self,
        x: np.ndarray,
        y: np.ndarray,
        name: str = CENTROID_NAME,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Centroids:
        """Add centroids."""
        layer = self.try_reuse(name, Centroids, reuse=reuse)
        color = kwargs.pop("color", as_array("line", CANVAS))
        width = kwargs.pop("width", 5)
        if layer:
            layer.data = np.c_[x, y]
            layer.visible = kwargs.get("visible", True)
        else:
            layer = self.viewer.add_centroids(np.c_[x, y], name=name, color=color, width=width, **kwargs)
        return layer

    def add_inf_centroids(
        self,
        x: np.ndarray,
        name: str = CENTROID_NAME,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> InfLine:
        """Add centroids."""
        layer = self.try_reuse(name, InfLine, reuse=reuse)
        color = kwargs.pop("color", as_array("line", CANVAS))
        if layer:
            layer.data = x
            layer.visible = kwargs.get("visible", True)
        else:
            layer = self.viewer.add_inf_line(x, orientation="vertical", name=name, color=color, **kwargs)
        return layer

    def add_region(
        self,
        window: tuple[float, float],
        name: str = REGION_NAME,
        editable: bool = True,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Region | None:
        """Add region of interest."""
        # get currently selected layers
        try:
            layer = self.try_reuse(name, Region, reuse=reuse)
            color = kwargs.pop("color", as_array("highlight", CANVAS))
            if layer:
                update_layer_attributes(layer, False, data=(window, "vertical"), color=color, **kwargs)
            else:
                layer = self.viewer.add_region((window, "vertical"), name=name, color=color, **kwargs)
            # set editable flag
            layer.editable = editable
        except TypeError:
            return None
        else:
            return layer

    def add_regions(
        self,
        window: tuple[float | int, float | int],
        name: str = REGION_NAME,
        editable: bool = True,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Region:
        """Add a region of interest."""
        # get currently selected layers
        layer = self.try_reuse(name, Region, reuse=reuse)
        color = kwargs.pop("color", as_array("highlight", CANVAS))
        if layer:
            update_layer_attributes(layer, False, data=window, **kwargs)
        else:
            layer = self.viewer.add_region(window, orientation="vertical", name=name, color=color, **kwargs)
        # set editable flag
        layer.editable = editable
        return layer

    def add_extract_region_layer(self) -> Region | None:
        """Add region of interest layer."""
        if self.region_layer is None:
            self.region_layer = self.viewer.add_region(
                ((0, 0.1), "vertical"),
                name=EXTRACT_NAME,
                color=as_array("scatter", CANVAS),
                opacity=0.5,
            )
        self.select_one_layer(self.region_layer)
        return self.region_layer

    def remove_region_layers(self) -> None:
        """Remove all region layers from the plot."""
        layers = self.get_layers_of_type(Region)
        self.remove_layers(layers)

    def set_line_x(self, x: np.ndarray) -> None:
        """Update x-axis data of all line layers where the dimension of `x` matches that of the currently
        present data
        .
        """
        layers = self.get_layers_of_type(Line)
        for layer in layers:
            data = layer.data
            if data.shape[0] == len(x):
                data[:, 0] = x
                layer.data = data

    def clear(self) -> None:
        """Clear canvas and reset what plots leave behind (categorical axes, log scales, legend and title)."""
        super().clear()
        self.viewer.reset_plot()
        self.set_title("")

    def set_title(self, title: str) -> None:
        """Show `title` at the top of the canvas (empty string hides it)."""
        self.viewer.text_overlay.text = title
        self.viewer.text_overlay.position = "top_center"
        self.viewer.text_overlay.visible = bool(title)

    def set_limits(self, x: tuple[float, float] | None = None, y: tuple[float, float] | None = None) -> None:
        """Set the visible x and/or y range in data units."""
        xmin, xmax, ymin, ymax = self.viewer.camera.rect
        xmin, xmax = x if x is not None else (xmin, xmax)
        ymin, ymax = y if y is not None else (ymin, ymax)
        self.viewer.camera.set_rect(xmin, xmax, ymin, ymax)

    def add_dotted_line(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        name: str = "Dotted line",
        color: ty.Any = None,
        size: float = 3,
        n_points: int = 60,
        reuse: bool = True,
        **kwargs: ty.Any,
    ) -> Scatter:
        """Draw a dotted polyline through (`x`, `y`) as evenly spaced markers.

        napari-plot lines cannot be dashed, so dotted/dashed reference lines are drawn as a Scatter layer with
        `n_points` markers (sized in screen pixels) spread uniformly along the path length.
        """
        if color is None:
            color = as_array("axis", CANVAS)
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        steps = np.hypot(np.diff(x), np.diff(y))
        distance = np.r_[0.0, np.cumsum(steps)]
        if len(x) < 2 or distance[-1] == 0:
            samples_x, samples_y = x, y
        else:
            targets = np.linspace(0.0, distance[-1], max(int(n_points), 2))
            samples_x, samples_y = np.interp(targets, distance, x), np.interp(targets, distance, y)
        kwargs.setdefault("scaling", False)
        return self.add_scatter(samples_x, samples_y, name=name, color=color, size=size, reuse=reuse, **kwargs)

    def plot_roc(
        self,
        fpr: dict[ty.Any, np.ndarray],
        tpr: dict[ty.Any, np.ndarray],
        labels: dict[ty.Any, str],
        plot_micro: bool = True,
        plot_macro: bool = True,
        title: str = "ROC Curves",
        **_kwargs: ty.Any,
    ) -> None:
        """Plot ROC curves (one per key of `fpr`), dotted micro/macro averages and the chance diagonal."""
        from seaborn import color_palette

        self.clear()
        colors = iter(color_palette(n_colors=max(len(fpr), 1)))
        entries = []
        for index, key in enumerate(fpr):
            label = str(labels[key])
            if key in ("micro", "macro"):
                if (key == "micro" and not plot_micro) or (key == "macro" and not plot_macro):
                    continue
                color = "deeppink" if key == "micro" else "royalblue"
                self.add_dotted_line(fpr[key], tpr[key], name=f"roc {key}", color=color, size=4, n_points=80)
                entries.append({"label": label, "marker": "disc", "color": color})
            else:
                color = (*next(colors), 1.0)
                self.plot(fpr[key], tpr[key], name=f"roc {index}", color=color, width=2)
                entries.append({"label": label, "marker": "hbar", "color": color})
        self.add_dotted_line([0, 1], [0, 1], name="roc chance")
        self.viewer.axis.x_label = "False Positive Rate"
        self.viewer.axis.y_label = "True Positive Rate"
        self._finish_ml_plot(entries, title, x=(-0.05, 1.0), y=(0.0, 1.05), position="bottom_right")

    def plot_precision_recall(
        self,
        precision: dict[ty.Any, np.ndarray],
        recall: dict[ty.Any, np.ndarray],
        labels: dict[ty.Any, str],
        plot_micro: bool = True,
        title: str = "Precision-Recall Curve",
        **_kwargs: ty.Any,
    ) -> None:
        """Plot precision-recall curves (one per key of `precision`) with a dotted micro average."""
        from seaborn import color_palette

        self.clear()
        colors = iter(color_palette(n_colors=max(len(precision), 1)))
        entries = []
        for index, key in enumerate(precision):
            label = str(labels[key])
            if key == "micro":
                if not plot_micro:
                    continue
                self.add_dotted_line(recall[key], precision[key], name="pr micro", color="royalblue", size=4)
                entries.append({"label": label, "marker": "disc", "color": "royalblue"})
            else:
                color = (*next(colors), 1.0)
                self.plot(recall[key], precision[key], name=f"pr {index}", color=color, width=2)
                entries.append({"label": label, "marker": "hbar", "color": color})
        self.viewer.axis.x_label = "Recall"
        self.viewer.axis.y_label = "Precision"
        self._finish_ml_plot(entries, title, x=(0.0, 1.05), y=(0.0, 1.05), position="bottom_left")

    def plot_calibration(
        self,
        y_true: np.ndarray,
        y_probas: np.ndarray,
        classes: list[str],
        title: str = "Calibration Curve",
        n_bins: int = 10,
        **_kwargs: ty.Any,
    ) -> None:
        """Plot per-class calibration curves against the dotted "perfectly calibrated" diagonal."""
        from seaborn import color_palette
        from sklearn.calibration import calibration_curve

        self.clear()
        y_true, y_probas = np.asarray(y_true), np.asarray(y_probas)
        entries = []
        for index, (cls_name, rgb) in enumerate(zip(classes, color_palette(n_colors=max(len(classes), 1)))):
            probas = y_probas[:, index] if y_probas.ndim == 2 else y_probas
            fraction_pos, mean_pred = calibration_curve(
                (y_true == index).astype(int),
                probas,
                n_bins=n_bins,
                strategy="uniform",
            )
            color = (*rgb, 1.0)
            self.plot(mean_pred, fraction_pos, name=f"calibration {index}", color=color, width=2)
            entries.append({"label": str(cls_name), "marker": "hbar", "color": color})
        self.add_dotted_line([0, 1], [0, 1], name="calibration ideal")
        entries.append({"label": "Perfectly calibrated", "marker": "disc", "color": as_array("axis", CANVAS)})
        self.viewer.axis.x_label = "Predicted Probability"
        self.viewer.axis.y_label = "True Probability"
        self._finish_ml_plot(entries, title, x=(0.0, 1.05), y=(0.0, 1.05), position="top_left")

    def plot_confusion_matrix(
        self,
        matrix: np.ndarray,
        labels: list[str],
        which: str = "counts",
        title: str = "Confusion Matrix",
        cmap: ty.Any = "rocket",
        **_kwargs: ty.Any,
    ) -> list:
        """Plot an annotated confusion matrix (`which` is "counts", "percentage" or "counts_and_percentage")."""
        matrix = np.asarray(matrix)
        total = max(float(np.sum(matrix)), 1.0)
        labels = [str(label) for label in labels]
        self.clear()
        if which == "counts":
            layers = self.viewer.heatmap(matrix, annot=True, fmt="d", cmap=cmap, xticklabels=labels, yticklabels=labels)
        elif which == "percentage":
            layers = self.viewer.heatmap(
                matrix / total,
                annot=True,
                fmt=".2%",
                cmap=cmap,
                xticklabels=labels,
                yticklabels=labels,
            )
        else:
            annot = np.asarray([f"{value:0.0f}\n{value / total:.2%}" for value in matrix.ravel()]).reshape(matrix.shape)
            layers = self.viewer.heatmap(matrix, annot=annot, fmt="", cmap=cmap, xticklabels=labels, yticklabels=labels)
        self.viewer.axis.x_label = "Predicted"
        self.viewer.axis.y_label = "Actual"
        self.set_title(title)
        return layers

    def plot_precision_recall_f1_support(
        self,
        scores: dict[str, dict[str, float]],
        labels: list[str],
        title: str = "Classification Report",
        cmap: ty.Any = "Blues",
        **_kwargs: ty.Any,
    ) -> list:
        """Plot the classification report as an annotated `class x metric` heatmap (values in 0-1)."""
        metrics = list(scores)
        grid = np.asarray([[scores[metric][cls] for metric in metrics] for cls in labels], dtype=float)
        self.clear()
        layers = self.viewer.heatmap(
            grid,
            vmin=0,
            vmax=1,
            cmap=cmap,
            annot=True,
            fmt="0.3f",
            xticklabels=metrics,
            yticklabels=[str(label) for label in labels],
        )
        self.viewer.axis.x_label = ""
        self.viewer.axis.y_label = ""
        self.set_title(title)
        return layers

    def _finish_ml_plot(
        self,
        entries: list[dict],
        title: str,
        x: tuple[float, float],
        y: tuple[float, float],
        position: str,
    ) -> None:
        """Apply legend, title and fixed limits shared by the curve plots."""
        if entries:
            self.viewer.set_legend(entries, position=position)
        self.set_title(title)
        self.set_limits(x=x, y=y)


if __name__ == "__main__":  # pragma: no cover
    from qtextra.config.theme import THEMES
    from qtextra.helpers import make_btn
    from qtextra.utils.dev import exec_, qframe

    def _main(frame, ha) -> tuple:
        def _on_btn() -> None:
            n_bins = np.random.default_rng().integers(5, 100, 1)[0]
            rel_width = np.random.rand(1)
            wrapper.add_histogram(a, n_bins, rel_width=rel_width)

        wrapper = NapariLineView(frame)
        THEMES.set_theme_stylesheet(wrapper.widget)

        a = np.arange(10)
        # viewer.add_histogram(a, 9)

        wrapper.plot(np.arange(100), np.random.random(100))
        wrapper.add_extract_region_layer()

        # viewer.add_centroids(np.arange(100), np.random.default_rng().integers(0, 1000, 100))

        ha.addWidget(wrapper.widget, stretch=True)
        ha.addWidget(make_btn(frame, "Click me", func=_on_btn))

    app, frame, ha = qframe(horz=False)
    frame.setMinimumSize(600, 600)
    _main(frame, ha)  # type: ignore[no-untyped-call]
    frame.show()
    exec_(app)
