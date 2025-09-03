"""Typing utilities."""

import typing as ty
from enum import Enum

Callback = ty.Union[ty.Callable, ty.Sequence[ty.Callable]]
Orientation = ty.Literal["horizontal", "vertical"]
