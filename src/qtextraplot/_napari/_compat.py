"""Compatibility fixes for supported napari versions."""

from __future__ import annotations

import typing as ty
from enum import Enum
from functools import wraps

from napari.layers import Layer


def install_mode_enum_compatibility() -> None:
    """Allow layers to accept equivalent string enums from stale modules."""
    original = Layer._mode_setter_helper
    if getattr(original, "_qtextraplot_normalizes_mode_enums", False):
        return

    @wraps(original)
    def _mode_setter_helper(self: Layer, mode_in: ty.Any) -> ty.Any:
        if isinstance(mode_in, Enum) and not isinstance(mode_in, self._modeclass):
            try:
                mode_in = self._modeclass[mode_in.name]
            except KeyError:
                if isinstance(mode_in.value, str):
                    mode_in = mode_in.value
        return original(self, mode_in)

    _mode_setter_helper._qtextraplot_normalizes_mode_enums = True  # type: ignore[attr-defined]
    Layer._mode_setter_helper = _mode_setter_helper
