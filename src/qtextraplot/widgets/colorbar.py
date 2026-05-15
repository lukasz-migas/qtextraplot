"""SCiLS-style colorbar widgets."""

from __future__ import annotations

import math
import typing as ty
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
from qtpy.QtCore import QPointF, QRectF, QSignalBlocker, Qt, Signal
from qtpy.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPen, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from superqt.sliders import QDoubleRangeSlider

ColorbarInput = np.ndarray | QImage | QPixmap | str | tuple[float, ...] | list[float] | None
RangeTuple = tuple[float, float]


@dataclass(frozen=True)
class ColorbarStackItem:
    """Configuration for one row in a colorbar stack."""

    label: str = ""
    data_range: RangeTuple = (0.0, 1.0)
    limits: RangeTuple | None = None
    colorbar: ColorbarInput = None


def _normalize_range(value: tuple[float, float]) -> RangeTuple:
    lower, upper = float(value[0]), float(value[1])
    if lower <= upper:
        return lower, upper
    return upper, lower


def _format_percent(numerator: float, denominator: float) -> str:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or math.isclose(denominator, 0.0):
        return "0%"
    return f"{round((numerator / denominator) * 100.0)}%"


def _format_overflow_percent(data_max: float, selected_max: float) -> str:
    if not math.isfinite(data_max) or not math.isfinite(selected_max) or math.isclose(selected_max, 0.0):
        return ""
    percent = (data_max / selected_max) * 100.0
    if percent <= 100.0:
        return ""
    return f"{round(percent)}%"


def _array_to_uint8_rgba(array: np.ndarray) -> np.ndarray:
    data = np.asarray(array)
    data = np.squeeze(data)
    if data.ndim == 1 and data.size in (3, 4):
        data = data.reshape(1, data.size)
    if data.ndim == 3:
        data = data[data.shape[0] // 2]
    if data.ndim != 2:
        return np.array([[0, 0, 0, 255], [255, 255, 255, 255]], dtype=np.uint8)
    if data.shape[-1] == 1:
        data = np.repeat(data, 3, axis=-1)
    if data.shape[-1] not in (3, 4):
        return np.array([[0, 0, 0, 255], [255, 255, 255, 255]], dtype=np.uint8)

    data = np.nan_to_num(data.astype(float, copy=False), nan=0.0, posinf=255.0, neginf=0.0)
    if data.size and data.max() <= 1.0:
        data = data * 255.0
    data = np.clip(data, 0.0, 255.0).astype(np.uint8)
    if data.shape[-1] == 3:
        alpha = np.full((*data.shape[:-1], 1), 255, dtype=np.uint8)
        data = np.concatenate((data, alpha), axis=-1)
    return data


def _sample_color_stops(colors: np.ndarray, max_stops: int = 32) -> list[tuple[float, QColor]]:
    if len(colors) == 0:
        return [(0.0, QColor("#000000")), (1.0, QColor("#ffffff"))]
    indices = np.linspace(0, len(colors) - 1, min(max_stops, len(colors))).astype(int)
    stops: list[tuple[float, QColor]] = []
    last_index = max(len(colors) - 1, 1)
    for index in indices:
        rgba = colors[index]
        stops.append(
            (
                float(index / last_index),
                QColor(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])),
            ),
        )
    if stops[0][0] != 0.0:
        rgba = colors[0]
        stops.insert(0, (0.0, QColor(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))))
    if stops[-1][0] != 1.0:
        rgba = colors[-1]
        stops.append((1.0, QColor(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))))
    return stops


def _color_stops_from_image(image: QImage) -> list[tuple[float, QColor]]:
    if image.isNull() or image.width() <= 0:
        return [(0.0, QColor("#000000")), (1.0, QColor("#ffffff"))]
    y = max(0, image.height() // 2)
    indices = np.linspace(0, image.width() - 1, min(32, image.width())).astype(int)
    stops: list[tuple[float, QColor]] = []
    denominator = max(image.width() - 1, 1)
    for index in indices:
        stops.append((float(index / denominator), QColor(image.pixel(int(index), y))))
    return stops


def _colorbar_to_stops(colorbar: ColorbarInput) -> list[tuple[float, QColor]]:
    if colorbar is None:
        return [(0.0, QColor("#000000")), (1.0, QColor("#ffffff"))]
    if isinstance(colorbar, QPixmap):
        return _color_stops_from_image(colorbar.toImage())
    if isinstance(colorbar, QImage):
        return _color_stops_from_image(colorbar)
    if isinstance(colorbar, str):
        color = QColor(colorbar)
        if color.isValid():
            return [(0.0, QColor("#000000")), (1.0, color)]
        return [(0.0, QColor("#000000")), (1.0, QColor("#ffffff"))]

    colors = _array_to_uint8_rgba(np.asarray(colorbar))
    if colors.ndim == 2 and colors.shape[0] == 1:
        color = colors[0]
        return [(0.0, QColor("#000000")), (1.0, QColor(int(color[0]), int(color[1]), int(color[2]), int(color[3])))]
    return _sample_color_stops(colors)


class _ColorbarSliderBar(QDoubleRangeSlider):
    detailRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setBarVisible(False)
        self._color_stops = _colorbar_to_stops(None)
        self._minimum_label = "0%"
        self._maximum_label = "100%"

    def set_colorbar(self, colorbar: ColorbarInput) -> None:
        """Set the colorbar preview used to paint the slider."""
        self._color_stops = _colorbar_to_stops(colorbar)
        self.update()

    def set_percent_labels(self, minimum: str, maximum: str) -> None:
        """Set the labels painted below the handles."""
        self._minimum_label = minimum
        self._maximum_label = maximum
        self.update()

    def mousePressEvent(self, event) -> None:
        """Open details on right-click, otherwise drag handles normally."""
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            self.detailRequested.emit()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        """Paint the checkerboard, color ramp, handles, and percent labels."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bar_rect = self._bar_rect()
        low, high = self.value()
        minimum_x = self._value_to_x(float(low), bar_rect)
        maximum_x = self._value_to_x(float(high), bar_rect)
        minimum_x, maximum_x = min(minimum_x, maximum_x), max(minimum_x, maximum_x)

        self._draw_checkerboard(
            painter,
            QRectF(bar_rect.left(), bar_rect.top(), max(0.0, minimum_x - bar_rect.left()), bar_rect.height()),
        )
        self._draw_gradient(
            painter,
            QRectF(minimum_x, bar_rect.top(), max(1.0, maximum_x - minimum_x), bar_rect.height()),
        )
        self._draw_overflow(
            painter,
            QRectF(maximum_x, bar_rect.top(), max(0.0, bar_rect.right() - maximum_x), bar_rect.height()),
        )
        self._draw_border(painter, bar_rect)
        self._draw_handles(painter, minimum_x, maximum_x, bar_rect)
        self._draw_percent_labels(painter, minimum_x, maximum_x, bar_rect)

    def _bar_rect(self) -> QRectF:
        contents = self.contentsRect()
        return QRectF(
            float(contents.left() + 8),
            float(contents.top() + 8),
            float(max(1, contents.width() - 16)),
            18.0,
        )

    def _value_to_x(self, value: float, rect: QRectF) -> float:
        minimum = float(self.minimum())
        maximum = float(self.maximum())
        if math.isclose(maximum, minimum):
            return float(rect.left())
        ratio = (value - minimum) / (maximum - minimum)
        ratio = max(0.0, min(1.0, ratio))
        return float(rect.left() + ratio * rect.width())

    def _draw_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return
        square = 7
        light = QColor("#b7b7b7")
        dark = QColor("#595959")
        left = math.floor(rect.left())
        top = math.floor(rect.top())
        right = math.ceil(rect.right())
        bottom = math.ceil(rect.bottom())
        for y in range(top, bottom, square):
            for x in range(left, right, square):
                color = light if ((x - left) // square + (y - top) // square) % 2 == 0 else dark
                painter.fillRect(x, y, square, square, color)

    def _draw_gradient(self, painter: QPainter, rect: QRectF) -> None:
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return
        gradient = QLinearGradient(QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y()))
        for stop, color in self._color_stops:
            gradient.setColorAt(stop, color)
        painter.fillRect(rect, QBrush(gradient))

    def _draw_overflow(self, painter: QPainter, rect: QRectF) -> None:
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return
        painter.fillRect(rect, self._color_stops[-1][1])

    def _draw_border(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#151515"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    def _draw_handles(self, painter: QPainter, minimum_x: float, maximum_x: float, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#202020"), 5))
        for x in (minimum_x, maximum_x):
            painter.drawLine(QPointF(x, rect.top() - 4.0), QPointF(x, rect.bottom() + 4.0))
        painter.setPen(QPen(QColor("#ffffff"), 3))
        for x in (minimum_x, maximum_x):
            painter.drawLine(QPointF(x, rect.top() - 4.0), QPointF(x, rect.bottom() + 4.0))

    def _draw_percent_labels(self, painter: QPainter, minimum_x: float, maximum_x: float, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#f0f0f0"), 1))
        font_metrics = painter.fontMetrics()
        y = int(rect.bottom() + font_metrics.ascent() + 8)
        self._draw_centered_text(painter, self._minimum_label, minimum_x, y)
        self._draw_centered_text(painter, self._maximum_label, maximum_x, y)

    def _draw_centered_text(self, painter: QPainter, text: str, x: float, y: int) -> None:
        if not text:
            return
        font_metrics = painter.fontMetrics()
        width = font_metrics.horizontalAdvance(text)
        left = int(max(0, min(self.width() - width, x - width / 2)))
        painter.drawText(left, y, text)


class QtColorbarRangeSlider(QWidget):
    """Colorbar row with draggable minimum and maximum limits."""

    limitsChanged = Signal(tuple)
    valueChanged = Signal(tuple)
    rangeChanged = Signal(tuple)
    detailRequested = Signal()

    def __init__(self, parent: QWidget | None = None, label: str = "", colorbar: ColorbarInput = None) -> None:
        super().__init__(parent)
        self._data_range: RangeTuple = (0.0, 1.0)
        self._label = QLabel(label, self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._label.setVisible(bool(label))

        self._slider = _ColorbarSliderBar(self)
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        self._slider.rangeChanged.connect(self._on_slider_range_changed)
        self._slider.detailRequested.connect(self.detailRequested.emit)

        self._overflow_label = QLabel("", self)
        self._overflow_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._overflow_label.setMinimumWidth(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._label)
        layout.addWidget(self._slider, stretch=1)
        layout.addWidget(self._overflow_label)

        self.setFocusProxy(self._slider)
        self.set_colorbar(colorbar)
        self.set_data_range(self._data_range)
        self.set_limits(self._data_range)

    @property
    def slider(self) -> QDoubleRangeSlider:
        """Return the internal range slider."""
        return self._slider

    def set_label(self, text: str) -> None:
        """Set the left-hand label text."""
        self._label.setText(text)
        self._label.setVisible(bool(text))

    def set_data_range(self, value: RangeTuple) -> None:
        """Set the full data range represented by the colorbar."""
        data_range = _normalize_range(value)
        self._data_range = data_range
        blocker = QSignalBlocker(self._slider)
        self._slider.setRange(*data_range)
        del blocker
        low, high = self.limits()
        self.set_limits((max(data_range[0], min(low, data_range[1])), max(data_range[0], min(high, data_range[1]))))
        self._update_labels()
        if not self.signalsBlocked():
            self.rangeChanged.emit(data_range)

    def set_limits(self, value: RangeTuple) -> None:
        """Set the selected visible intensity limits."""
        low, high = _normalize_range(value)
        data_low, data_high = self._data_range
        low = max(data_low, min(low, data_high))
        high = max(data_low, min(high, data_high))
        if low > high:
            low, high = high, low
        self._slider.setValue((low, high))
        self._update_labels()

    def limits(self) -> RangeTuple:
        """Return the selected visible intensity limits."""
        low, high = self._slider.value()
        return float(low), float(high)

    def set_colorbar(self, colorbar: ColorbarInput) -> None:
        """Set the colorbar preview image or color."""
        self._slider.set_colorbar(colorbar)

    def setSingleStep(self, value: float) -> None:
        """Set the slider step size."""
        self._slider.setSingleStep(value)

    def setRange(self, minimum: float, maximum: float) -> None:
        """Set the full data range represented by the colorbar."""
        self.set_data_range((minimum, maximum))

    def setValue(self, value: RangeTuple) -> None:
        """Set the selected visible intensity limits."""
        self.set_limits(value)

    def value(self) -> RangeTuple:
        """Return the selected visible intensity limits."""
        return self.limits()

    def _on_slider_range_changed(self, minimum: float, maximum: float) -> None:
        self._data_range = float(minimum), float(maximum)
        self._update_labels()
        if not self.signalsBlocked():
            self.rangeChanged.emit(self._data_range)

    def _on_slider_value_changed(self, value: tuple[float, float]) -> None:
        limits = float(value[0]), float(value[1])
        self._update_labels()
        if self.signalsBlocked():
            return
        self.limitsChanged.emit(limits)
        self.valueChanged.emit(limits)

    def _update_labels(self) -> None:
        low, high = self.limits()
        data_max = self._data_range[1]
        self._slider.set_percent_labels(_format_percent(low, high), "100%")
        self._overflow_label.setText(_format_overflow_percent(data_max, high))


class QtColorbarStack(QWidget):
    """Vertical stack of colorbar range sliders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._widgets: list[QtColorbarRangeSlider] = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

    @property
    def widgets(self) -> tuple[QtColorbarRangeSlider, ...]:
        """Return colorbar row widgets."""
        return tuple(self._widgets)

    def set_items(self, items: Iterable[ColorbarStackItem | Mapping[str, ty.Any]]) -> None:
        """Replace the stack with the provided colorbar rows."""
        self._clear()
        for item in items:
            stack_item = self._coerce_item(item)
            widget = QtColorbarRangeSlider(self, label=stack_item.label, colorbar=stack_item.colorbar)
            widget.set_data_range(stack_item.data_range)
            widget.set_limits(stack_item.limits if stack_item.limits is not None else stack_item.data_range)
            self._widgets.append(widget)
            self._layout.addWidget(widget)
        self._layout.addStretch(1)

    def _clear(self) -> None:
        while self._layout.count():
            layout_item = self._layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()
        self._widgets.clear()

    def _coerce_item(self, item: ColorbarStackItem | Mapping[str, ty.Any]) -> ColorbarStackItem:
        if isinstance(item, ColorbarStackItem):
            return item
        return ColorbarStackItem(
            label=str(item.get("label", "")),
            data_range=ty.cast(RangeTuple, item.get("data_range", (0.0, 1.0))),
            limits=ty.cast(RangeTuple | None, item.get("limits")),
            colorbar=ty.cast(ColorbarInput, item.get("colorbar")),
        )


__all__ = ["ColorbarStackItem", "QtColorbarRangeSlider", "QtColorbarStack"]
