"""Tests for reusable colorbar widgets."""

from qtextraplot.widgets import ColorbarStackItem, QtColorbarRangeSlider, QtColorbarStack
from qtextraplot.widgets.colorbar import _format_overflow_percent, _format_percent


def test_percent_formatting() -> None:
    assert _format_percent(30.0, 100.0) == "30%"
    assert _format_percent(0.0, 0.0) == "0%"
    assert _format_overflow_percent(288.0, 100.0) == "288%"
    assert _format_overflow_percent(100.0, 100.0) == ""
    assert _format_overflow_percent(10.0, 0.0) == ""


def test_colorbar_range_slider_updates_labels(qtbot) -> None:
    widget = QtColorbarRangeSlider(label="703.5724 m/z +/- 21.3 ppm", colorbar="magenta")
    qtbot.addWidget(widget)

    widget.set_data_range((0.0, 200.0))
    widget.set_limits((60.0, 100.0))

    assert widget.value() == (60.0, 100.0)
    assert widget._slider._minimum_label == "60%"
    assert widget._slider._maximum_label == "100%"
    assert widget._overflow_label.text() == "200%"
    assert not widget.grab().isNull()


def test_colorbar_range_slider_emits_limits_changed(qtbot) -> None:
    widget = QtColorbarRangeSlider()
    qtbot.addWidget(widget)
    widget.set_data_range((0.0, 100.0))

    with qtbot.waitSignal(widget.limitsChanged, timeout=1000) as blocker:
        widget.set_limits((10.0, 50.0))

    assert blocker.args == [(10.0, 50.0)]


def test_colorbar_stack_replaces_items(qtbot) -> None:
    stack = QtColorbarStack()
    qtbot.addWidget(stack)

    stack.set_items(
        [
            ColorbarStackItem(label="A", data_range=(0.0, 10.0), limits=(2.0, 5.0), colorbar="red"),
            {"label": "B", "data_range": (0.0, 20.0), "limits": (6.0, 10.0), "colorbar": "blue"},
        ],
    )

    assert len(stack.widgets) == 2
    assert stack.widgets[0].value() == (2.0, 5.0)
    assert stack.widgets[1].value() == (6.0, 10.0)

    stack.set_items([])
    assert stack.widgets == ()
