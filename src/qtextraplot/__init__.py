"""Extra widgets for Qt."""

from importlib.metadata import PackageNotFoundError, version

from loguru import logger

try:
    __version__ = version("qtextraplot")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Lukasz G. Migas"
__email__ = "lukas.migas@yahoo.com"
__issue_url__ = "https://github.com/lukasz-migas/qtextraplot-issues/issues"
__project_url__ = "https://lukasz-migas.com/qtextraplot"
logger.disable("qtextraplot")
