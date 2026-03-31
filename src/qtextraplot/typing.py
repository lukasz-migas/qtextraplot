"""Typing utilities."""

import typing as ty

Callback = ty.Union[ty.Callable, ty.Sequence[ty.Callable]]
Orientation = ty.Literal["horizontal", "vertical"]
