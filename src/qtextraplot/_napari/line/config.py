"""Configuration file."""

from napari.utils.events import EventedModel


class Config(EventedModel):
    """Configuration for line plot."""

    auto_zoom: bool = False
