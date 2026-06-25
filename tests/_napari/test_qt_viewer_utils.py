"""Tests for shared Qt viewer helpers."""

from __future__ import annotations

import typing as ty
from types import SimpleNamespace

from qtpy.QtWidgets import QWidget

from qtextraplot._napari._qt_viewer_utils import (
    QtViewerInstanceTracker,
    calc_status_from_cursor,
    forward_key_event_to_canvas,
    set_mouse_over_status,
    show_controls_dialog,
    toggle_controls_dialog,
)


class _TrackedWidget(QtViewerInstanceTracker, QWidget):
    _instances: ty.ClassVar[list[QWidget]] = []
    _instance_index = -1


class _FakeDialog:
    def __init__(self, _parent):
        self.visible = False
        self.raised = False
        self.activated = False

    def show(self):
        self.visible = True

    def raise_(self):
        self.raised = True

    def activateWindow(self):
        self.activated = True

    def isVisible(self):
        return self.visible

    def setVisible(self, visible):
        self.visible = visible


class _FakeKeyEvent:
    def __init__(self) -> None:
        self.accepted = False

    def accept(self) -> None:
        self.accepted = True


class _FakeSceneBackend:
    def __init__(self) -> None:
        self.calls = []

    def _keyEvent(self, event_type, event) -> None:
        self.calls.append((event_type, event))


class _FakeCanvas:
    def __init__(self) -> None:
        self._scene_canvas = SimpleNamespace(
            _backend=_FakeSceneBackend(),
            events=SimpleNamespace(key_press=object(), key_release=object()),
        )


def test_instance_tracker_tracks_current_widget(qtbot):
    first = _TrackedWidget()
    second = _TrackedWidget()
    qtbot.addWidget(first)
    qtbot.addWidget(second)

    first._register_instance()
    second._register_instance()

    assert _TrackedWidget.current() is second
    _TrackedWidget.set_current_index(first)
    assert _TrackedWidget.current() is first


def test_calc_status_from_cursor_uses_active_layer_tooltip():
    active = SimpleNamespace(
        _loaded=True,
        get_status=lambda *args, **kwargs: {"coordinates": (1, 2)},
        _get_tooltip_text=lambda *args, **kwargs: "value=42",
    )
    viewer = SimpleNamespace(
        mouse_over_canvas=True,
        layers=SimpleNamespace(selection=SimpleNamespace(active=active)),
        cursor=SimpleNamespace(position=(1.2, 2.4), _view_direction=(0, 0)),
        dims=SimpleNamespace(displayed=(0, 1)),
        tooltip=SimpleNamespace(visible=True),
    )

    assert calc_status_from_cursor(viewer) == ({"coordinates": (1, 2)}, "value=42")


def test_calc_status_from_cursor_falls_back_to_coordinates():
    viewer = SimpleNamespace(
        mouse_over_canvas=True,
        layers=SimpleNamespace(selection=SimpleNamespace(active=None)),
        cursor=SimpleNamespace(position=(1.2, 2.6)),
        dims=SimpleNamespace(displayed=(0, 1)),
        tooltip=SimpleNamespace(visible=False),
    )

    assert calc_status_from_cursor(viewer) == ("[1 3]", "[1 3]")


def test_set_mouse_over_status_updates_viewer_state():
    viewer = SimpleNamespace(status="", mouse_over_canvas=False)

    set_mouse_over_status(viewer, True)
    assert viewer.status == "Ready"
    assert viewer.mouse_over_canvas is True

    set_mouse_over_status(viewer, False)
    assert viewer.status == ""
    assert viewer.mouse_over_canvas is False


def test_show_controls_dialog_reuses_dialog_instance():
    widget = SimpleNamespace(_disable_controls=False, _layers_controls_dialog=None)

    show_controls_dialog(widget, _FakeDialog)
    dialog = widget._layers_controls_dialog

    assert dialog is not None
    assert dialog.visible is True
    assert dialog.raised is True
    assert dialog.activated is True

    show_controls_dialog(widget, _FakeDialog)
    assert widget._layers_controls_dialog is dialog


def test_toggle_controls_dialog_opens_then_toggles_visibility():
    widget = SimpleNamespace(_disable_controls=False, _layers_controls_dialog=None)

    toggle_controls_dialog(widget, lambda: show_controls_dialog(widget, _FakeDialog))
    assert widget._layers_controls_dialog.visible is True

    toggle_controls_dialog(widget, lambda: None)
    assert widget._layers_controls_dialog.visible is False


def test_forward_key_event_to_canvas_forwards_to_scene_backend() -> None:
    canvas = _FakeCanvas()
    event = _FakeKeyEvent()

    forward_key_event_to_canvas(canvas, event, "key_press")

    assert event.accepted is True
    assert canvas._scene_canvas._backend.calls == [(canvas._scene_canvas.events.key_press, event)]
