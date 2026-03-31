"""
Streaming Dashboard Widget
──────────────────────────
Stat cards with live-streaming plots.

Public API on StatCard
───────────────────────
  card.append_point(y, x=None)
      Append a single sample.  x defaults to (last_x + 1).

  card.append_points(ys, xs=None)
      Append an array of samples at once.

  card.set_data(x, y)
      Replace all data (same as initial seed).

  card.set_value(text)
      Update the header label directly (used when not hovered).

Streaming behaviour
───────────────────
  • Line/scatter: if max_points is set, a rolling window is kept.
  • When the view is NOT zoomed (or after double-click reset), the x-axis
    follows the tail automatically.  While zoomed, new data is added silently
    without moving the viewport.
  • Y-axis always auto-fits the *visible* x-window + 5 % buffer.

Interaction
───────────
  • Drag left-button → horizontal rubber-band zoom.
  • Double-click     → reset to full / following view.
  • Hover            → crosshair + snap dot; header shows hovered value.
  • Mouse leave      → crosshair hidden; header reverts to latest value.

Requirements:
    pip install qtpy pyqtgraph numpy
    Works with PyQt5, PyQt6, PySide2, or PySide6.

Run:
    python dashboard_widget.py
"""

from __future__ import annotations

import sys

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer
from qtpy.QtGui import QBrush, QColor, QCursor, QFont, QPalette, QPen
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ── palette ───────────────────────────────────────────────────────────────────
BG_CARD = "#1e1e1e"
BG_APP = "#141414"
ACCENT = "#e8a020"
ACCENT2 = "#3a8fd4"
TEXT_TITLE = "#9a9a9a"
TEXT_VALUE = "#f0f0f0"
TEXT_UNIT = "#9a9a9a"
FILL_ALPHA = 55
DRAG_FILL = QColor(232, 160, 32, 40)
DRAG_EDGE = QColor(232, 160, 32, 200)
Y_BUFFER = 0.05


# ── helpers ───────────────────────────────────────────────────────────────────


def amber_pen(width=2):
    return pg.mkPen(color=ACCENT, width=width)


def amber_brush(alpha=FILL_ALPHA):
    c = QColor(ACCENT)
    c.setAlpha(alpha)
    return pg.mkBrush(c)


# ── x-only rubber-band ViewBox ────────────────────────────────────────────────


class ZoomViewBox(pg.ViewBox):
    """
    Horizontal-only drag-to-zoom.  Tracks whether the user has manually
    zoomed so the streaming tail-follow can be suppressed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseEnabled(x=False, y=False)
        self._drag_start: float | None = None
        self._drag_cur: float | None = None
        self._dragging = False
        self.user_zoomed = False  # public flag for StatCard
        self._xd: np.ndarray | None = None
        self._yd: np.ndarray | None = None

    # ── data registration (for y-refit) ──────────────────────────────────────

    def set_data_arrays(self, x: np.ndarray, y: np.ndarray):
        self._xd = x
        self._yd = y

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_start = ev.pos().x()
            self._drag_cur = ev.pos().x()
            self._dragging = False
            ev.accept()
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._drag_start is not None and (ev.buttons() & Qt.LeftButton):
            self._dragging = True
            self._drag_cur = ev.pos().x()
            self.update()
            ev.accept()
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._dragging:
            x0, x1 = self._drag_start, self._drag_cur
            if abs(x1 - x0) > 4:
                lx = self.mapToView(QPointF(min(x0, x1), 0)).x()
                rx = self.mapToView(QPointF(max(x0, x1), 0)).x()
                self._apply_xrange(lx, rx)
                self.user_zoomed = True
            self._drag_start = self._drag_cur = None
            self._dragging = False
            self.update()
            ev.accept()
        else:
            self._drag_start = self._drag_cur = None
            self._dragging = False
            super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.user_zoomed = False
            self.autoRange()
            ev.accept()
        else:
            super().mouseDoubleClickEvent(ev)

    def wheelEvent(self, ev, axis=None):
        """
        Scroll wheel zooms the x-axis around the mouse cursor position.
        Each notch scales by WHEEL_FACTOR (< 1 = zoom in, > 1 = zoom out).
        Y-axis is refitted to visible data afterwards.
        Double-click still resets to full view.
        """
        WHEEL_FACTOR = 0.85  # zoom ratio per 120-unit wheel step
        # pyqtgraph passes a QGraphicsSceneWheelEvent; delta() is in 1/8 degrees
        try:
            delta = ev.delta()  # PyQt5 / PySide2
        except AttributeError:
            delta = ev.angleDelta().y()  # PyQt6 / PySide6

        if delta == 0:
            ev.accept()
            return

        steps = delta / 120.0  # positive = scroll up = zoom in
        factor = WHEEL_FACTOR**steps  # <1 when zooming in, >1 when out

        # current x range
        vr = self.viewRange()
        xmin, xmax = vr[0]
        span = xmax - xmin

        # anchor zoom at the mouse x position in data coordinates
        mouse_data_x = self.mapToView(ev.pos()).x()
        # clamp anchor so it stays inside current range
        anchor = max(xmin, min(xmax, mouse_data_x))
        # fraction of span to the left/right of anchor
        left_frac = (anchor - xmin) / span if span else 0.5
        right_frac = 1.0 - left_frac

        new_span = span * factor
        new_xmin = anchor - left_frac * new_span
        new_xmax = anchor + right_frac * new_span

        # clamp to data bounds so we never zoom out past the data
        if self._xd is not None and len(self._xd):
            data_xmin = float(self._xd.min())
            data_xmax = float(self._xd.max())
            new_xmin = max(new_xmin, data_xmin)
            new_xmax = min(new_xmax, data_xmax)
            # if span collapsed below 2 samples, abort
            if new_xmax - new_xmin < (data_xmax - data_xmin) / max(len(self._xd), 1):
                ev.accept()
                return

        self._apply_xrange(new_xmin, new_xmax)

        # if we zoomed all the way back out, resume tail-following
        if self._xd is not None and len(self._xd):
            full_span = float(self._xd.max()) - float(self._xd.min())
            if (new_xmax - new_xmin) >= full_span * 0.999:
                self.user_zoomed = False
            else:
                self.user_zoomed = True

        ev.accept()

    # ── range helpers ─────────────────────────────────────────────────────────

    def _apply_xrange(self, xmin: float, xmax: float):
        self.setXRange(xmin, xmax, padding=0)
        self._refit_y(xmin, xmax)

    def _refit_y(self, xmin: float, xmax: float):
        if self._xd is None or self._yd is None or len(self._xd) == 0:
            return
        mask = (self._xd >= xmin) & (self._xd <= xmax)
        if not mask.any():
            return
        yv = self._yd[mask]
        ylo, yhi = float(yv.min()), float(yv.max())
        span = (yhi - ylo) or 1.0
        buf = span * Y_BUFFER
        self.setYRange(ylo - buf, yhi + buf, padding=0)

    def refit_y_full(self):
        if self._xd is None or len(self._xd) == 0:
            return
        self._refit_y(float(self._xd.min()), float(self._xd.max()))

    def follow_tail(self, window: int | None = None):
        """
        Scroll the x-axis to show the last `window` samples (or all if None),
        then refit y.  Called by StatCard on every append when not user_zoomed.
        """
        if self._xd is None or len(self._xd) == 0:
            return
        xmax = float(self._xd[-1])
        xmin = float(self._xd[-window]) if window is not None and len(self._xd) > window else float(self._xd[0])
        self._apply_xrange(xmin, xmax)

    def autoRange(self, *args, **kwargs):
        super().autoRange(*args, **kwargs)
        self.refit_y_full()

    # ── rubber-band paint ─────────────────────────────────────────────────────

    def paint(self, p, *args):
        super().paint(p, *args)
        if self._dragging and self._drag_start is not None:
            x0 = min(self._drag_start, self._drag_cur)
            x1 = max(self._drag_start, self._drag_cur)
            p.save()
            p.setPen(QPen(DRAG_EDGE, 1, Qt.SolidLine))
            p.setBrush(QBrush(DRAG_FILL))
            p.drawRect(QRectF(x0, 0, x1 - x0, self.rect().height()))
            p.restore()


# ── hover overlay ─────────────────────────────────────────────────────────────


class HoverOverlay:
    """Crosshair vline + snap dot, hidden on mouse leave."""

    def __init__(self, pw: pg.PlotWidget, plot_type: str, on_hover=None):
        self.pw = pw
        self.plot_type = plot_type
        self.on_hover = on_hover
        self._xd: np.ndarray | None = None
        self._yd: np.ndarray | None = None
        self._last_idx = None

        pi = pw.getPlotItem()

        self.vline = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=ACCENT, width=1, style=Qt.DashLine),
        )
        self.vline.setVisible(False)
        pi.addItem(self.vline, ignoreBounds=True)

        self.dot = pg.ScatterPlotItem(
            size=9,
            symbol="o",
            pen=pg.mkPen(ACCENT, width=2),
            brush=pg.mkBrush(BG_CARD),
        )
        self.dot.setVisible(False)
        pi.addItem(self.dot, ignoreBounds=True)

        pw.scene().sigMouseMoved.connect(self._on_move)

        # Leave event via event filter
        class _LeaveFilter(QObject):
            def eventFilter(self_, obj, ev):
                if ev.type() == QEvent.Leave:
                    self._on_leave()
                return False

        self._filter = _LeaveFilter(pw)
        vp = pw.viewport()
        vp.setMouseTracking(True)
        vp.installEventFilter(self._filter)

    def set_data(self, x: np.ndarray, y: np.ndarray):
        self._xd = np.asarray(x, float)
        self._yd = np.asarray(y, float)
        self._last_idx = None

    @property
    def active(self) -> bool:
        return self.vline.isVisible()

    def _on_move(self, scene_pos):
        pi = self.pw.getPlotItem()
        vb = pi.getViewBox()
        if isinstance(vb, ZoomViewBox) and vb._dragging:
            self._hide_gfx()
            return
        if not vb.sceneBoundingRect().contains(scene_pos):
            return
        mp = vb.mapSceneToView(scene_pos)
        mx, my = mp.x(), mp.y()
        if self._xd is None or len(self._xd) == 0:
            return

        if self.plot_type in ("line", "histogram"):
            idx = int(np.argmin(np.abs(self._xd - mx)))
        else:
            vr = vb.viewRange()
            xs = (vr[0][1] - vr[0][0]) or 1.0
            ys = (vr[1][1] - vr[1][0]) or 1.0
            idx = int(np.argmin(((self._xd - mx) / xs) ** 2 + ((self._yd - my) / ys) ** 2))

        sx, sy = float(self._xd[idx]), float(self._yd[idx])
        self.vline.setPos(sx)
        self.vline.setVisible(True)
        self.dot.setData([sx], [sy])
        self.dot.setVisible(True)

        if idx != self._last_idx:
            self._last_idx = idx
            if self.on_hover:
                self.on_hover(sx, sy)

    def _on_leave(self):
        self._hide_gfx()
        self._last_idx = None
        if self.on_hover:
            self.on_hover(None, None)

    def _hide_gfx(self):
        self.vline.setVisible(False)
        self.dot.setVisible(False)


# ── plot widget factory ───────────────────────────────────────────────────────


def _make_pw() -> pg.PlotWidget:
    vb = ZoomViewBox()
    pw = pg.PlotWidget(background=BG_CARD, viewBox=vb)
    pw.setMenuEnabled(False)
    pw.hideAxis("left")
    pw.hideAxis("bottom")
    pw.setFixedHeight(80)
    pw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    pi = pw.getPlotItem()
    pi.setContentsMargins(0, 0, 0, 0)
    pi.layout.setContentsMargins(0, 0, 0, 0)
    pw.viewport().setCursor(QCursor(Qt.CrossCursor))
    return pw


# ── stat card ─────────────────────────────────────────────────────────────────


class StatCard(QFrame):
    """
    A dashboard card with an embedded streaming plot.

    Parameters
    ----------
    title, value, unit, icon : display strings
    plot_type : "line" | "histogram" | "scatter"
    fmt       : Python format string applied to the hovered/latest y value
    prefix    : string prepended to the formatted value (e.g. "£ ")
    max_points: rolling window size for line/scatter (None = unlimited)
    follow_window: how many x-units to show when tail-following
                   (None = show all data)

    Streaming API
    -------------
    append_point(y, x=None)   – add one sample
    append_points(ys, xs=None) – add many samples
    set_data(x, y)            – replace all data
    set_value(text)           – update header label (when not hovered)
    """

    def __init__(
        self,
        title: str,
        value: str,
        unit: str = "",
        icon: str = "",
        plot_type: str = "line",
        fmt: str = "{:.2f}",
        prefix: str = "",
        max_points: int | None = None,
        follow_window: int | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.plot_type = plot_type
        self._base_value = value
        self._fmt = fmt
        self._prefix = prefix
        self._max_points = max_points
        self._follow_window = follow_window

        # internal data storage (always full arrays for fast ops)
        self._xd = np.empty(0, dtype=float)
        self._yd = np.empty(0, dtype=float)
        # next auto-x counter
        self._next_x = 0.0

        self._build_ui(title, value, unit, icon)
        self._init_plot_items()

        # hover overlay
        self._hover = HoverOverlay(self.plot_widget, plot_type, on_hover=self._on_hover)

        # give ViewBox a reference to our arrays (updated in-place on append)
        self._vb: ZoomViewBox = self.plot_widget.getPlotItem().getViewBox()

        # seed with demo data so the card isn't empty at startup
        self._seed()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self, title, value, unit, icon):
        self.setObjectName("StatCard")
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background: {BG_CARD};
                border-radius: 18px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 0)
        root.setSpacing(2)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color:{TEXT_TITLE}; background:transparent;")
        lbl_t.setFont(QFont("Segoe UI", 11))
        hdr.addWidget(lbl_t)
        hdr.addStretch()
        if icon:
            lbl_i = QLabel(icon)
            lbl_i.setStyleSheet(f"color:{ACCENT2}; background:transparent;")
            lbl_i.setFont(QFont("Segoe UI", 16))
            hdr.addWidget(lbl_i)
        root.addLayout(hdr)

        vrow = QHBoxLayout()
        vrow.setContentsMargins(0, 4, 0, 6)
        vrow.setSpacing(6)
        vrow.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color:{TEXT_VALUE}; background:transparent;")
        self.lbl_value.setFont(QFont("Segoe UI", 32, QFont.Light))
        vrow.addWidget(self.lbl_value)
        if unit:
            lbl_u = QLabel(unit)
            lbl_u.setStyleSheet(f"color:{TEXT_UNIT}; background:transparent;")
            lbl_u.setFont(QFont("Segoe UI", 13))
            lbl_u.setAlignment(Qt.AlignBottom)
            vrow.addWidget(lbl_u)
        vrow.addStretch()
        root.addLayout(vrow)

        self.plot_widget = _make_pw()
        root.addWidget(self.plot_widget)

    # ── plot item initialisation ──────────────────────────────────────────────

    def _init_plot_items(self):
        """Create the pyqtgraph items that will be updated on each append."""
        pi = self.plot_widget.getPlotItem()

        if self.plot_type == "line":
            # Two PlotDataItems share data with FillBetweenItem
            self._line_bottom = pg.PlotDataItem([], [], pen=None)
            self._line_top = pg.PlotDataItem([], [], pen=amber_pen(2))
            self._fill = pg.FillBetweenItem(
                self._line_bottom,
                self._line_top,
                brush=amber_brush(),
            )
            pi.addItem(self._fill)
            pi.addItem(self._line_bottom)
            pi.addItem(self._line_top)

        elif self.plot_type == "histogram":
            self._bar_item = pg.BarGraphItem(
                x=[],
                height=[],
                width=1,
                brush=amber_brush(),
                pen=amber_pen(1),
            )
            pi.addItem(self._bar_item)
            self._hist_bins = 30  # rebinned on each update

        else:  # scatter
            self._scatter_item = pg.ScatterPlotItem(
                x=[],
                y=[],
                pen=None,
                brush=amber_brush(90),
                size=7,
                symbol="o",
            )
            pi.addItem(self._scatter_item)

    # ── demo seed ─────────────────────────────────────────────────────────────

    def _seed(self):
        rng = np.random.default_rng(id(self) % (2**31))
        if self.plot_type == "line":
            n = 80
            y = np.cumsum(rng.normal(0, 0.3, n)) + 5
            y = np.clip(y, 0, None)
            x = np.arange(n, dtype=float)
        elif self.plot_type == "histogram":
            y = rng.normal(50, 15, 400)
            x = np.arange(len(y), dtype=float)
        else:
            x = rng.uniform(0, 10, 60)
            y = 0.8 * x + rng.normal(0, 1.2, 60)
            order = np.argsort(x)
            x, y = x[order], y[order]
        self.set_data(x, y)

    # ── internal redraw ───────────────────────────────────────────────────────

    def _redraw(self):
        """Push current _xd/_yd to plot items and update view."""
        x, y = self._xd, self._yd

        if self.plot_type == "line":
            zeros = np.zeros_like(x)
            self._line_bottom.setData(x, zeros)
            self._line_top.setData(x, y)

        elif self.plot_type == "histogram":
            if len(y) < 2:
                return
            counts, edges = np.histogram(y, bins=self._hist_bins)
            centres = (edges[:-1] + edges[1:]) / 2
            width = float(centres[1] - centres[0]) if len(centres) > 1 else 1.0
            self._bar_item.setOpts(
                x=centres,
                height=counts,
                width=width * 0.85,
            )
            # expose binned data to hover + viewbox
            x = centres.astype(float)
            y = counts.astype(float)

        else:  # scatter
            self._scatter_item.setData(x=x, y=y)

        # keep hover overlay and viewbox in sync
        self._hover.set_data(x, y)
        self._vb.set_data_arrays(x, y)

        # update view: follow tail unless user has zoomed
        if not self._vb.user_zoomed:
            self._vb.follow_tail(self._follow_window)

        # update header label if not being hovered
        if not self._hover.active and len(y):
            self._update_header_value(float(y[-1]))

    def _update_header_value(self, y: float):
        try:
            txt = self._prefix + self._fmt.format(y)
        except Exception:
            txt = str(y)
        self._base_value = txt
        self.lbl_value.setText(txt)
        self.lbl_value.setStyleSheet(f"color:{TEXT_VALUE}; background:transparent;")

    # ── hover callback ────────────────────────────────────────────────────────

    def _on_hover(self, x, y):
        if x is None:
            self.lbl_value.setText(self._base_value)
            self.lbl_value.setStyleSheet(f"color:{TEXT_VALUE}; background:transparent;")
        else:
            try:
                txt = self._prefix + self._fmt.format(y)
            except Exception:
                txt = str(y)
            self.lbl_value.setText(txt)
            self.lbl_value.setStyleSheet(f"color:{ACCENT}; background:transparent;")

    # ── rolling-window enforcement ────────────────────────────────────────────

    def _trim(self):
        if self._max_points and len(self._xd) > self._max_points:
            self._xd = self._xd[-self._max_points :]
            self._yd = self._yd[-self._max_points :]

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC STREAMING API
    # ══════════════════════════════════════════════════════════════════════════

    def append_point(self, y: float, x: float | None = None):
        """
        Append a single (x, y) sample and redraw.

        Parameters
        ----------
        y : new data value
        x : x-coordinate.  If None, auto-increments from the last x by 1.
        """
        if x is None:
            x = self._next_x
        self._next_x = float(x) + 1.0

        self._xd = np.append(self._xd, float(x))
        self._yd = np.append(self._yd, float(y))
        self._trim()
        self._redraw()

    def append_points(self, ys, xs=None):
        """
        Append multiple samples at once and redraw once.

        Parameters
        ----------
        ys : array-like of y values
        xs : array-like of x values, or None to auto-increment.
        """
        ys = np.asarray(ys, dtype=float)
        xs = np.arange(len(ys), dtype=float) + self._next_x if xs is None else np.asarray(xs, dtype=float)
        self._next_x = float(xs[-1]) + 1.0

        self._xd = np.concatenate([self._xd, xs])
        self._yd = np.concatenate([self._yd, ys])
        self._trim()
        self._redraw()

    def set_data(self, x, y):
        """
        Replace all data and redraw.

        Parameters
        ----------
        x, y : array-like
        """
        self._xd = np.asarray(x, dtype=float)
        self._yd = np.asarray(y, dtype=float)
        if len(self._xd):
            self._next_x = float(self._xd[-1]) + 1.0
        self._redraw()
        # defer initial full-range fit until widget is shown
        QTimer.singleShot(0, self._vb.refit_y_full)

    def set_value(self, text: str):
        """Directly set the header label (bypasses hover logic)."""
        self._base_value = text
        if not self._hover.active:
            self.lbl_value.setText(text)
            self.lbl_value.setStyleSheet(f"color:{TEXT_VALUE}; background:transparent;")


# ── demo dashboard ────────────────────────────────────────────────────────────


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard  ·  drag → zoom x  ·  dbl-click → reset")
        self.setStyleSheet(f"background:{BG_APP};")
        self.resize(940, 520)

        grid = QGridLayout(self)
        grid.setContentsMargins(24, 24, 24, 24)
        grid.setSpacing(16)

        # title, value, unit, icon, plot_type, fmt, prefix, max_pts, follow_win, row, col
        specs = [
            ("Electricity cost", "£ 4.35", "", "£", "line", "{:.2f}", "£ ", 500, 60, 0, 0),
            ("Electricity usage", "12.20", "kWh", "⚡", "line", "{:.2f}", "", 500, None, 0, 1),
            ("Temperature", "21.4", "°C", "🌡", "histogram", "{:.1f}", "", 500, None, 1, 0),
            ("Heart rate", "72", "bpm", "♥", "scatter", "{:.0f}", "", 500, 80, 1, 1),
        ]

        self.cards: dict[str, StatCard] = {}
        for title, val, unit, icon, ptype, fmt, prefix, maxp, win, row, col in specs:
            card = StatCard(
                title,
                val,
                unit,
                icon,
                ptype,
                fmt,
                prefix,
                max_points=maxp,
                follow_window=win,
            )
            grid.addWidget(card, row, col)
            self.cards[title] = card

        # streaming demo: push one sample to each line/scatter card every 200 ms
        self._rng = np.random.default_rng(0)
        self._cost_y = 4.35
        self._usage_y = 12.20
        self._temp_y = 21.4
        self._hr_y = 72.0

        stream_timer = QTimer(self)
        stream_timer.timeout.connect(self._stream_tick)
        stream_timer.start(50)

        # histogram gets a fresh batch every 2 s
        hist_timer = QTimer(self)
        hist_timer.timeout.connect(self._hist_tick)
        hist_timer.start(50)

    def _stream_tick(self):
        rng = self._rng
        self._cost_y += rng.normal(0, 0.04)
        self._usage_y += rng.normal(0, 0.10)
        self._hr_y += rng.normal(0, 0.8)
        self._hr_y = float(np.clip(self._hr_y, 50, 110))

        self.cards["Electricity cost"].append_point(self._cost_y)
        self.cards["Electricity usage"].append_point(self._usage_y)
        self.cards["Heart rate"].append_point(self._hr_y)

    def _hist_tick(self):
        # append 20 temperature readings per tick so the histogram rebuilds
        temps = self._rng.normal(21.4, 1.5, 20)
        self.cards["Temperature"].append_points(temps)
        self._temp_y = float(temps[-1])


# ── entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pg.setConfigOption("background", BG_APP)
    pg.setConfigOption("foreground", TEXT_TITLE)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG_APP))
    pal.setColor(QPalette.WindowText, QColor(TEXT_VALUE))
    pal.setColor(QPalette.Base, QColor(BG_CARD))
    pal.setColor(QPalette.AlternateBase, QColor("#1a1a1a"))
    pal.setColor(QPalette.ToolTipBase, QColor(BG_CARD))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT_VALUE))
    pal.setColor(QPalette.Text, QColor(TEXT_VALUE))
    pal.setColor(QPalette.Button, QColor(BG_CARD))
    pal.setColor(QPalette.ButtonText, QColor(TEXT_VALUE))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#000000"))
    app.setPalette(pal)

    win = Dashboard()
    win.show()
    sys.exit(app.exec())
