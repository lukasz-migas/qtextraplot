"""Tests for qtextraplot's napari-plot line integration."""

from __future__ import annotations

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("napari_plot", reason="napari-plot is not installed")

from app_model.backends.qt import QModelMenu  # noqa: E402
from napari._app_model import get_app_model  # noqa: E402
from napari._app_model.constants import MenuId  # noqa: E402
from napari._app_model.context import get_context  # noqa: E402
from napari._qt._qapp_model import build_qmodel_menu  # noqa: E402
from napari._qt.containers.qt_layer_model import LockedRole  # noqa: E402
from napari.components import LayerList  # noqa: E402
from napari_plot.viewer import ViewerModel  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402
from qtpy.QtCore import QPoint, Qt  # noqa: E402
from qtpy.QtWidgets import QWidget  # noqa: E402

from qtextraplot._napari.line.component_controls.qt_view_toolbar import QtViewRightToolbar  # noqa: E402
from qtextraplot._napari.line.wrapper import NapariLineView  # noqa: E402


def test_line_toolbar_controls_napari_plot_legend(qtbot) -> None:
    """The embedded toolbar should control napari-plot's native legend."""
    viewer = ViewerModel()

    class DummyQtViewer(QWidget):
        """Small Qt viewer stand-in for toolbar tests."""

        def __init__(self) -> None:
            super().__init__()
            self.viewer = viewer

        def on_toggle_controls_dialog(self) -> None:
            """No-op layer controls toggle."""

        def clipboard(self) -> None:
            """No-op clipboard action."""

        def on_save_figure(self) -> None:
            """No-op save action."""

    qt_viewer = DummyQtViewer()
    view = QWidget()
    qtbot.addWidget(qt_viewer)
    qtbot.addWidget(view)
    toolbar = QtViewRightToolbar(view=view, viewer=viewer, qt_viewer=qt_viewer)
    qtbot.addWidget(toolbar)

    assert not viewer.legend.visible
    assert not toolbar.tools_legend_btn.isChecked()

    toolbar._toggle_legend_visible(True)

    assert viewer.legend.visible
    assert toolbar.tools_legend_btn.isChecked()


def test_line_view_reuses_scatter_and_applies_per_point_colors(qtbot, _mock_opengl_capabilities) -> None:
    """Scatter updates should retain the layer and propagate point colors."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False)
    qtbot.addWidget(view.widget)

    layer = view.add_scatter([1.0, 2.0], [3.0, 4.0], name="points", color=["red", "blue"], symbol="o")
    updated = view.add_scatter([2.0], [5.0], name="points", color=["green"], symbol="s")

    assert updated is layer
    np.testing.assert_allclose(layer.face_color, [[0.0, 0.5019608, 0.0, 1.0]])
    np.testing.assert_allclose(layer.border_color, [[0.0, 0.5019608, 0.0, 1.0]])
    assert layer.symbol.tolist() == ["square"]


def test_line_layer_context_menu_uses_napari_context_keys(qtbot, _mock_opengl_capabilities) -> None:
    """The napari 0.10 layer menu should evaluate against plot-layer contexts."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(view.widget)
    view.plot([0.0, 1.0], [0.0, 1.0], name="line")

    context = get_context(view.viewer.layers)
    menu = build_qmodel_menu(MenuId.LAYERLIST_CONTEXT, parent=view.widget.layers)

    assert "any_selected_layers_deletion_locked" in context
    menu.update_from_context(context)
    get_app_model().commands.execute_command("napari.layer.duplicate").result()

    assert len(view.viewer.layers) == 2
    assert type(view.viewer.layers[1]) is type(view.viewer.layers[0])


def test_line_layer_context_menu_toggles_lock_on_clicked_view(
    qtbot: QtBot,
    _mock_opengl_capabilities: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Route the native lock action to the embedded list even with another viewer current."""
    parent = QWidget()
    qtbot.addWidget(parent)
    plot = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(plot.widget)
    plot_layer = plot.viewer.add_line([[0, 0], [1, 1]])
    other = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(other.widget)
    other_layer = other.viewer.add_line([[2, 2], [3, 3]])
    active_layers = get_app_model().injection_store.provide(LayerList)
    assert getattr(active_layers, "__wrapped__", active_layers) is other.viewer.layers

    def toggle_lock(menu: QModelMenu, _position: QPoint) -> None:
        action = next(action for action in menu.actions() if action.objectName() == "napari.layer.toggle_lock")
        assert action.isEnabled()
        action.trigger()

    monkeypatch.setattr(QModelMenu, "exec", toggle_lock)
    layer_list = plot.widget.layers
    model = layer_list.model()
    index = model.index(0, 0)
    for locked in (True, False):
        layer_list.itemDelegate().show_context_menu(index, model, QPoint(), layer_list)
        assert bool(plot_layer.locked) is locked
        assert bool(index.data(LockedRole)) is locked
        assert not other_layer.locked


@pytest.mark.xfail(reason="flaky")
def test_line_view_forwards_modified_double_clicks(qtbot, _mock_opengl_capabilities) -> None:
    """Ctrl-double-click should reach viewer callbacks with world coordinates."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False)
    qtbot.addWidget(view.widget)
    view.widget.resize(400, 300)
    view.widget.show()
    received: list[tuple[float, ...]] = []

    def on_double_click(_viewer: object, event: object) -> None:
        """Record the callback's world coordinate."""
        received.append(tuple(event.position))  # type: ignore[attr-defined]

    view.viewer.mouse_double_click_callbacks.append(on_double_click)

    qtbot.mouseDClick(
        view.widget.canvas.native,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier,
        pos=QPoint(200, 150),
    )

    assert len(received) == 1


class _FakeMouseEvent:
    """Mutable stand-in for napari's read-only mouse event."""

    def __init__(self, pos: tuple[float, float], position: tuple[float, float], button: int = 1) -> None:
        self.type = "mouse_press"
        self.pos = np.asarray(pos)
        self.position = position
        self.button = button


def _run_drag_callback(callback, event: _FakeMouseEvent, moves: list[tuple[float, float]]) -> None:
    """Drive mouse drag generator the same way napari does."""
    gen = callback(None, event)
    try:
        next(gen)
    except StopIteration:
        return
    for pos in moves:
        event.type = "mouse_move"
        event.pos = np.asarray(pos)
        next(gen)
    event.type = "mouse_release"
    with pytest.raises(StopIteration):
        next(gen)


def test_line_view_connect_click(qtbot, _mock_opengl_capabilities) -> None:
    """Clicks without dragging are forwarded in data coordinates and drags/other buttons are ignored."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(view.widget)
    received: list[tuple[float, float]] = []

    callback = view.connect_click(lambda x, y: received.append((x, y)))
    assert callback in view.viewer.mouse_drag_callbacks

    # world coordinates are (y, x)
    _run_drag_callback(callback, _FakeMouseEvent((10, 10), (0.5, 200.0)), [(11, 10)])
    assert received == [(200.0, 0.5)]

    # dragging is a zoom, not a click
    _run_drag_callback(callback, _FakeMouseEvent((10, 10), (0.5, 200.0)), [(30, 10)])
    # right-click is ignored
    _run_drag_callback(callback, _FakeMouseEvent((10, 10), (0.5, 200.0), button=2), [])
    assert received == [(200.0, 0.5)]

    view.disconnect_click(callback)
    assert callback not in view.viewer.mouse_drag_callbacks


def test_line_view_close_removes_instance(qtbot, _mock_opengl_capabilities) -> None:
    """Closed views should not be kept alive by the instance list."""
    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    assert view in NapariLineView._instances
    view.close()
    assert view not in NapariLineView._instances


def test_line_view_histogram_uses_bar_centers(qtbot, _mock_opengl_capabilities) -> None:
    """Histogram bars should be centered on bins and reuse the same Bar layer."""
    from napari_plot.layers import Bar

    view = NapariLineView(None)
    qtbot.addWidget(view.widget)

    values = np.array([0.0, 0.5, 1.5, 2.5, 3.5, 3.9])
    layer = view.add_histogram(values, bins=4, rel_width=0.5)
    counts, edges = np.histogram(values, bins=4)

    assert isinstance(layer, Bar)
    np.testing.assert_allclose(layer.data[:, 0], (edges[:-1] + edges[1:]) / 2)
    np.testing.assert_allclose(layer.data[:, 1], counts)
    assert layer.width == pytest.approx(0.5 * np.diff(edges).mean())

    updated = view.add_histogram(values, bins=2)
    assert updated is layer
    assert len(layer.data) == 2


def test_line_view_new_layer_helpers_reuse_layers(qtbot, _mock_opengl_capabilities) -> None:
    """Bar, Band, ErrorBar and Text helpers should create once and update on reuse."""
    from napari_plot.layers import Band, Bar, ErrorBar, Text

    view = NapariLineView(None)
    qtbot.addWidget(view.widget)
    x = np.arange(5, dtype=float)

    bar = view.add_bar(x, x * 2, name="bars", orientation="horizontal", width=0.5)
    assert isinstance(bar, Bar)
    assert bar.orientation == "horizontal"
    assert view.add_bar(x[:3], x[:3], name="bars") is bar
    assert len(bar.data) == 3

    band = view.fill_between(x, x - 1, x + 1, name="band", opacity=0.5)
    assert isinstance(band, Band)
    assert band.opacity == pytest.approx(0.5)
    np.testing.assert_allclose(band.data[:, 1:], np.c_[x - 1, x + 1])
    assert view.fill_between(x, 1.0, name="band") is band
    np.testing.assert_allclose(band.data[:, 1:], np.c_[np.ones(5), np.zeros(5)])

    errors = view.add_error_bar(x, x, yerr=0.5, name="errors")
    assert isinstance(errors, ErrorBar)
    np.testing.assert_allclose(errors.data[:, 4:], 0.5)
    assert np.isnan(errors.data[:, 2:4]).all()
    assert view.add_error_bar(x, x, xerr=[np.zeros(5), np.ones(5)], name="errors") is errors
    np.testing.assert_allclose(errors.data[:, 3], 1.0)

    text = view.add_text([1.0, 2.0], [3.0, 4.0], ["a", "b"], name="labels")
    assert isinstance(text, Text)
    assert list(text.text) == ["a", "b"]
    assert view.add_text(1.0, 1.0, "c", name="labels") is text
    assert list(text.text) == ["c"]


def test_line_view_replaces_layer_of_other_type_with_same_name(qtbot, _mock_opengl_capabilities) -> None:
    """A legacy layer sharing the requested name should be replaced, not duplicated."""
    from napari_plot.layers import Bar

    view = NapariLineView(None)
    qtbot.addWidget(view.widget)
    view.plot(np.arange(3), np.arange(3), name="Histogram")

    layer = view.add_histogram(np.arange(10), bins=3)

    assert isinstance(layer, Bar)
    assert [lyr.name for lyr in view.viewer.layers] == ["Histogram"]


def test_line_view_shape_helpers_reuse_layers(qtbot, _mock_opengl_capabilities) -> None:
    """Rectangles, Vectors, MultiLine and Areas helpers should create once and update on reuse."""
    from napari_plot.layers import Areas, MultiLine, Rectangles, Vectors

    view = NapariLineView(None)
    qtbot.addWidget(view.widget)

    rects = view.add_rectangles([1.0, 2.0], [3.0, 4.0], height=2.0, width=[0.5, 1.0], name="rects")
    assert isinstance(rects, Rectangles)
    np.testing.assert_allclose(rects.data, [[1.0, 3.0, 2.0, 0.5], [2.0, 4.0, 2.0, 1.0]])
    assert view.add_rectangles([5.0], [6.0], 1.0, 1.0, name="rects") is rects
    np.testing.assert_allclose(rects.data, [[5.0, 6.0, 1.0, 1.0]])

    vectors = view.add_vectors([0.0, 1.0], [2.0, 3.0], dx=1.0, dy=[0.5, -0.5], name="arrows", vector_style="line")
    assert isinstance(vectors, Vectors)
    # napari stores (row, col) = (y, x) for both start and projection
    np.testing.assert_allclose(vectors.data[:, 0], [[2.0, 0.0], [3.0, 1.0]])
    np.testing.assert_allclose(vectors.data[:, 1], [[0.5, 1.0], [-0.5, 1.0]])
    assert view.add_vectors([0.0], [0.0], 1.0, 1.0, name="arrows") is vectors
    assert len(vectors.data) == 1

    x = np.arange(5, dtype=float)
    multi = view.add_multi_line(x, [x, x * 2, x * 3], name="multi", color=["red", "green", "blue"])
    assert isinstance(multi, MultiLine)
    assert len(multi.data["ys"]) == 3
    assert view.add_multi_line(x, [x], name="multi") is multi
    assert len(multi.data["ys"]) == 1

    area = np.c_[x, x - 1, x + 1]
    areas = view.add_areas([area, area + 10], name="areas", fill_color=["red", "blue"])
    assert isinstance(areas, Areas)
    assert len(areas.data) == 2
    assert view.add_areas([area], name="areas") is areas
    assert len(areas.data) == 1


def _make_view(qtbot) -> NapariLineView:
    view = NapariLineView(None, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(view.widget)
    return view


def test_line_view_clear_resets_plot_state(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    view.viewer.boxplot({"a": [1.0, 2.0, 3.0], "b": [2.0, 3.0, 4.0]})
    view.viewer.axis.y_scale = "log"
    view.set_title("Title")
    assert view.viewer.axis.x_categories == ("a", "b")

    view.clear()
    assert len(view.layers) == 0
    assert view.viewer.axis.x_categories is None
    assert view.viewer.axis.y_scale == "linear"
    assert not view.viewer.text_overlay.visible


def test_line_view_dotted_line_spreads_markers(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    layer = view.add_dotted_line([0, 1, 1], [0, 0, 1], n_points=5)
    # (y, x) data, evenly spaced along the 2-unit path
    np.testing.assert_allclose(layer.data[:, 1], [0, 0.5, 1, 1, 1])
    np.testing.assert_allclose(layer.data[:, 0], [0, 0, 0, 0.5, 1])
    assert not layer.scaling


def test_line_view_plot_roc(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    fpr = {0: np.array([0, 0.2, 1]), 1: np.array([0, 0.5, 1]), "micro": np.array([0, 0.3, 1])}
    tpr = {0: np.array([0, 0.8, 1]), 1: np.array([0, 0.6, 1]), "micro": np.array([0, 0.7, 1])}
    labels = {0: "class A", 1: "class B", "micro": "micro-average"}
    view.plot_roc(fpr, tpr, labels, plot_macro=False, title="ROC")

    names = [layer.name for layer in view.layers]
    assert names == ["roc 0", "roc 1", "roc micro", "roc chance"]
    assert [entry.label for entry in view.viewer.legend.entries] == ["class A", "class B", "micro-average"]
    assert view.viewer.text_overlay.text == "ROC"
    assert view.viewer.axis.x_label == "False Positive Rate"
    # the curves touch 0 and 1, so the fixed range leaves room for the line width and survives a view reset
    view.viewer.reset_view()
    assert view.viewer.camera.rect == (-0.02, 1.02, -0.02, 1.02)
    view.clear()
    assert view.viewer.camera.x_range is None
    assert view.viewer.camera.y_range is None


def test_line_view_plot_precision_recall_skips_micro(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    precision = {0: np.array([1, 0.5]), "micro": np.array([1, 0.4])}
    recall = {0: np.array([0, 1]), "micro": np.array([0, 1])}
    view.plot_precision_recall(precision, recall, {0: "A", "micro": "micro"}, plot_micro=False)
    assert [layer.name for layer in view.layers] == ["pr 0"]


def test_line_view_plot_calibration_adds_ideal_diagonal(qtbot, _mock_opengl_capabilities) -> None:
    pytest.importorskip("sklearn")
    view = _make_view(qtbot)
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, 200)
    probas = rng.random((200, 2))
    probas /= probas.sum(axis=1, keepdims=True)
    view.plot_calibration(y_true, probas, ["A", "B"])
    assert [layer.name for layer in view.layers] == ["calibration 0", "calibration 1", "calibration ideal"]
    assert view.viewer.legend.entries[-1].label == "Perfectly calibrated"


@pytest.mark.parametrize("which", ["counts", "percentage", "counts_and_percentage"])
def test_line_view_plot_confusion_matrix(qtbot, _mock_opengl_capabilities, which: str) -> None:
    view = _make_view(qtbot)
    view.plot_confusion_matrix(np.array([[5, 1], [2, 7]]), ["A", "B"], which=which)
    assert view.viewer.axis.x_categories == ("A", "B")
    assert view.viewer.axis.x_label == "Predicted"
    texts = [layer for layer in view.layers if "annotations" in layer.name]
    assert len(texts) == 1
    assert len(texts[0].data) == 4
    # whole cells are visible, including the outer half of the edge pixels
    assert view.viewer.camera.rect == (-0.5, 1.5, -0.5, 1.5)


def test_line_view_plot_classification_report(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    scores = {"precision": {"A": 0.5, "B": 0.9}, "recall": {"A": 0.6, "B": 0.8}}
    view.plot_precision_recall_f1_support(scores, ["A", "B"])
    assert view.viewer.axis.x_categories == ("precision", "recall")
    assert view.viewer.axis.y_categories == ("B", "A")


def test_line_view_wraps_long_y_category_labels(qtbot, _mock_opengl_capabilities) -> None:
    view = _make_view(qtbot)
    view.viewer.axis.y_categories = ("Test (Negative)", "Brain")
    assert view.widget.y_axis.node.axis.ticker.category_labels == ("Test\n(Negative)", "Brain")


def test_line_view_legend_helpers(qtbot, _mock_opengl_capabilities) -> None:
    """Legend helpers should forward to the napari-plot legend overlay."""
    view = NapariLineView(None)
    qtbot.addWidget(view.widget)

    view.set_legend([{"label": "A", "marker": "disc", "color": "red"}], position="bottom_right")
    assert view.viewer.legend.visible
    assert [entry.label for entry in view.viewer.legend.entries] == ["A"]

    view.clear_legend()
    assert not view.viewer.legend.visible
    assert not view.viewer.legend.entries

    view.plot(np.arange(3), np.arange(3), name="Series")
    view.set_legend_from_layers()
    assert [entry.label for entry in view.viewer.legend.entries] == ["Series"]


def test_line_view_point_picking(qtbot, _mock_opengl_capabilities, monkeypatch) -> None:
    """Hover, click and double-click report the nearest visible scatter point within the pixel tolerance."""
    import qtextraplot._napari.line.picking as picking_module

    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(view.widget)
    first = view.add_scatter([1.0, 5.0], [1.0, 5.0], name="first")
    second = view.add_scatter([9.0], [9.0], name="second")
    view.viewer.camera.rect = (0.0, 10.0, 0.0, 10.0)
    height, width = view.widget.canvas.size
    shown: list[str] = []
    monkeypatch.setattr(picking_module.QToolTip, "showText", lambda _pos, text, _widget: shown.append(text))
    clicked: list[tuple[str, int]] = []
    activated: list[tuple[str, int]] = []

    picker = view.connect_point_picking(
        ["first", second],
        on_hover=lambda layer, index: f"{layer.name}:{index}",
        on_click=lambda layer, index: clicked.append((layer.name, index)),
        on_double_click=lambda layer, index: activated.append((layer.name, index)),
        max_px=6,
    )
    near = 3.0 * 10.0 / max(width, height)  # data distance of ~3 pixels

    assert picker.pick(5.0 + near, 5.0) == (first, 1)
    assert picker.pick(9.0, 9.0 - near) == (second, 0)
    assert picker.pick(3.0, 3.0) is None
    second.visible = False
    assert picker.pick(9.0, 9.0) is None
    second.visible = True

    picker._on_move(None, _FakeMouseEvent((0, 0), (1.0, 1.0)))  # position is (y, x)
    assert shown == ["first:0"]

    _run_drag_callback(picker._click_callback, _FakeMouseEvent((10, 10), (5.0, 5.0)), [])
    assert clicked == [("first", 1)]

    picker._on_double_click(None, _FakeMouseEvent((0, 0), (9.0, 9.0)))
    assert activated == [("second", 0)]

    picker.disconnect()
    assert picker._on_move not in view.viewer.mouse_move_callbacks
    assert picker._on_double_click not in view.viewer.mouse_double_click_callbacks
    assert not any(callback is picker._click_callback for callback in view.viewer.mouse_drag_callbacks)


def test_nearest_point_handles_log_axes(qtbot, _mock_opengl_capabilities) -> None:
    """Distances are measured on the displayed (logarithmic) axis."""
    from qtextraplot._napari.line.picking import nearest_point

    parent = QWidget()
    qtbot.addWidget(parent)
    view = NapariLineView(parent, add_toolbars=False, connect_theme=False)
    qtbot.addWidget(view.widget)
    layer = view.add_scatter([1.0, 2.0], [10.0, 1000.0], name="points")
    view.viewer.axis.y_scale = "log"
    view.viewer.camera.rect = (0.0, 3.0, 1.0, 10000.0)

    assert nearest_point(view, [layer], 2.0, 900.0) == (layer, 1)
    assert nearest_point(view, [layer], 2.0, 100.0) is None
