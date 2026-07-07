"""Tests for safe napari image canvas wheel routing."""

from __future__ import annotations

from types import SimpleNamespace

from qtextraplot._napari.image._safe_wheel import install_safe_wheel_handler


class _FakeMouseWheelSignal:
    def __init__(self) -> None:
        self.disconnected: list[object] = []
        self.connected: list[object] = []

    def disconnect(self, callback: object) -> None:
        self.disconnected.append(callback)

    def connect(self, callback: object) -> None:
        self.connected.append(callback)


class _FakeViewboxEvents:
    def __init__(self) -> None:
        self.events: list[object] = []

    def mouse_wheel(self, event: object) -> None:
        self.events.append(event)
        event.handled = True


class _FakeCanvas:
    def __init__(self, viewbox: object | None) -> None:
        self.viewbox = viewbox
        self.scene_mouse_wheel = _FakeMouseWheelSignal()
        self._scene_canvas = SimpleNamespace(
            _process_mouse_event=object(),
            events=SimpleNamespace(mouse_wheel=self.scene_mouse_wheel),
        )

    def _get_viewbox_at(self, _pos: tuple[int, int]) -> tuple[object | None, tuple[int, int] | None]:
        return self.viewbox, (0, 0)


def _make_event(*, modifiers: tuple[str, ...] = (), handled: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        type="mouse_wheel",
        modifiers=modifiers,
        handled=handled,
        pos=(10, 20),
        button=None,
        buttons=[],
        delta=(0, 1),
        last_event=None,
        press_event=None,
    )


def test_install_safe_wheel_handler_replaces_scene_picking_handler() -> None:
    viewbox = SimpleNamespace(events=_FakeViewboxEvents())
    canvas = _FakeCanvas(viewbox)

    install_safe_wheel_handler(canvas)

    assert canvas.scene_mouse_wheel.disconnected == [canvas._scene_canvas._process_mouse_event]
    assert len(canvas.scene_mouse_wheel.connected) == 1


def test_safe_wheel_handler_routes_to_viewbox_without_picking() -> None:
    viewbox = SimpleNamespace(events=_FakeViewboxEvents())
    canvas = _FakeCanvas(viewbox)
    install_safe_wheel_handler(canvas)

    event = _make_event()
    canvas.scene_mouse_wheel.connected[0](event)

    assert event.handled is True
    assert len(viewbox.events.events) == 1


def test_safe_wheel_handler_ignores_modifier_wheel_events() -> None:
    viewbox = SimpleNamespace(events=_FakeViewboxEvents())
    canvas = _FakeCanvas(viewbox)
    install_safe_wheel_handler(canvas)

    event = _make_event(modifiers=("Control",))
    canvas.scene_mouse_wheel.connected[0](event)

    assert event.handled is False
    assert viewbox.events.events == []
