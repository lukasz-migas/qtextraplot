"""Plotting utilities."""


def update_attributes(layer, throw_exception: bool = True, **kwargs):
    """Update attributes on the layer."""
    for attr, value in kwargs.items():
        try:
            setattr(layer, attr, value)
        except (AttributeError, ValueError):
            if throw_exception:
                raise
