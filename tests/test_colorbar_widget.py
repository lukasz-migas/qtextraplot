"""Tests for reusable colorbar widgets."""

from qtextraplot.widgets import ColorbarStackItem, QtColorbarRangeSlider, QtColorbarStack, QtFloatingColorbarWidget
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


def test_colorbar_size_presets_change_row_height(qtbot) -> None:
    small = QtColorbarRangeSlider(size_preset="small")
    medium = QtColorbarRangeSlider(size_preset="medium")
    large = QtColorbarRangeSlider(size_preset="large")
    for widget in (small, medium, large):
        qtbot.addWidget(widget)

    assert small.slider.maximumHeight() < medium.slider.maximumHeight() < large.slider.maximumHeight()
    assert medium.slider.maximumHeight() <= 40


def test_colorbar_row_keeps_label_from_squashing_bar(qtbot) -> None:
    widget = QtColorbarRangeSlider(label="703.5724 m/z +/- 21.3 ppm", size_preset="medium")
    qtbot.addWidget(widget)

    assert widget._label.width() <= 185
    assert widget.slider.minimumWidth() >= 280
    assert widget.layout().spacing() <= 3


def test_colorbar_stack_size_preset_propagates(qtbot) -> None:
    stack = QtColorbarStack(size_preset="small")
    qtbot.addWidget(stack)
    stack.set_items([ColorbarStackItem(label="A", data_range=(0.0, 1.0), colorbar="red")])

    assert stack.widgets[0]._size_preset == "small"
    stack.set_size_preset("large")
    assert stack.widgets[0]._size_preset == "large"


def test_floating_colorbar_collapses_and_expands(qtbot) -> None:
    widget = QtFloatingColorbarWidget(title="Images")
    qtbot.addWidget(widget)
    widget.set_items([ColorbarStackItem(label="A", data_range=(0.0, 1.0), colorbar="red")])

    with qtbot.waitSignal(widget.collapsedChanged, timeout=1000) as blocker:
        widget.set_collapsed(True)

    assert blocker.args == [True]
    assert widget.is_collapsed()
    assert widget.stack.isHidden()

    widget.toggle_collapsed()
    assert not widget.is_collapsed()
    assert not widget.stack.isHidden()


def test_floating_colorbar_resizes_height_but_preserves_width(qtbot) -> None:
    widget = QtFloatingColorbarWidget(title="Images")
    qtbot.addWidget(widget)
    widget.resize(760, 200)

    widget.set_items(
        [
            ColorbarStackItem(label="A", data_range=(0.0, 1.0), colorbar="red"),
            ColorbarStackItem(label="B", data_range=(0.0, 1.0), colorbar="blue"),
        ],
    )
    height_with_two_rows = widget.height()

    widget.set_items([ColorbarStackItem(label="A", data_range=(0.0, 1.0), colorbar="red")])

    assert widget.width() == 760
    assert widget.height() < height_with_two_rows
