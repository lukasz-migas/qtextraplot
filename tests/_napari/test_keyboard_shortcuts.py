"""Tests for napari-backed viewer keyboard shortcuts."""

from __future__ import annotations

from types import MethodType

import pytest

pytest.importorskip("napari", reason="napari is not installed")
pytest.importorskip("napari_plot", reason="napari-plot is not installed")

from napari.utils.key_bindings import KeymapHandler, coerce_keybinding


def _has_key(viewer_type: type, shortcut: str) -> bool:
    return coerce_keybinding(shortcut) in viewer_type.class_keymap


def test_image_viewer_shortcuts_are_registered() -> None:
    from qtextraplot._napari.image.components.viewer_model import Viewer

    assert _has_key(Viewer, "Control-R")
    assert _has_key(Viewer, "Control-G")
    assert _has_key(Viewer, "V")


def test_line_viewer_shortcuts_are_registered() -> None:
    from qtextraplot._napari.line.components.viewer_model import Viewer

    assert _has_key(Viewer, "Control-R")
    assert _has_key(Viewer, "Control-G")
    assert _has_key(Viewer, "V")


def test_image_viewer_reset_shortcut_calls_reset_view() -> None:
    from qtextraplot._napari.image.components.viewer_model import Viewer

    called = []
    viewer = Viewer()
    object.__setattr__(viewer, "reset_view", MethodType(lambda self: called.append(self), viewer))
    handler = KeymapHandler()
    handler.keymap_providers = [viewer]

    assert handler.press_key("Control-R") is True
    assert called == [viewer]


def test_line_viewer_reset_shortcut_calls_reset_view() -> None:
    from qtextraplot._napari.line.components.viewer_model import Viewer

    called = []
    viewer = Viewer()
    object.__setattr__(viewer, "reset_view", MethodType(lambda self: called.append(self), viewer))
    handler = KeymapHandler()
    handler.keymap_providers = [viewer]

    assert handler.press_key("Control-R") is True
    assert called == [viewer]
