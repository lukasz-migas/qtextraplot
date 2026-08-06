"""Tests for qtextraplot's napari-plot line integration."""

from __future__ import annotations

import numpy as np
import pytest

napari = pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("napari_plot", reason="napari-plot is not installed")

from napari._app_model import get_app_model  # noqa: E402
from napari._app_model.constants import MenuId  # noqa: E402
from napari._app_model.context import get_context  # noqa: E402
from napari._qt._qapp_model import build_qmodel_menu  # noqa: E402
from napari_plot.viewer import ViewerModel  # noqa: E402
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
    """The napari 0.8 layer menu should evaluate against plot-layer contexts."""
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
