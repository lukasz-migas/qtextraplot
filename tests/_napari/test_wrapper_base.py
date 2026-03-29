"""Tests for viewer base helper behavior."""

from __future__ import annotations

from types import SimpleNamespace

from qtextraplot._napari._wrapper import ViewerBase


class _DummyViewerBase(ViewerBase):
    def __init__(self):
        self.viewer = SimpleNamespace(
            layers=[],
            text_overlay=SimpleNamespace(text="initial"),
        )
        self.widget = SimpleNamespace(canvas=None, view=SimpleNamespace(camera=None), close=lambda: None)


def test_clear_tracked_layers_sets_attributes_to_none():
    view = _DummyViewerBase()
    view.image_layer = object()
    view.mask_layer = object()

    view._clear_tracked_layers("image_layer", "mask_layer")

    assert view.image_layer is None
    assert view.mask_layer is None


def test_clear_tracked_layer_on_remove_only_clears_matching_layer():
    view = _DummyViewerBase()
    kept = SimpleNamespace(name="kept")
    removed = SimpleNamespace(name="removed")
    view.image_layer = kept
    view.mask_layer = removed

    view._clear_tracked_layer_on_remove(SimpleNamespace(name="removed"), "image_layer", "mask_layer")

    assert view.image_layer is kept
    assert view.mask_layer is None


def test_reset_text_overlay_is_tolerant_when_missing():
    view = _DummyViewerBase()
    view._reset_text_overlay()
    assert view.viewer.text_overlay.text == ""

    del view.viewer.text_overlay
    view._reset_text_overlay()
