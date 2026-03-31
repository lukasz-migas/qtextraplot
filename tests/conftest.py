"""Shared pytest configuration for qtextraplot."""

import os
import tempfile
from pathlib import Path

import appdirs
import pytest

# Tell qtextraplot it is running under pytest so test-specific guards activate.
os.environ["QTEXTRAPLOT_PYTEST"] = "1"

_TMP_DIR = Path(tempfile.mkdtemp(prefix="qtextraplot-pytest-"))
_NAPARI_CONFIG_DIR = _TMP_DIR / "napari-config"
_NAPARI_CACHE_DIR = _TMP_DIR / "napari-cache"
_MPL_CONFIG_DIR = _TMP_DIR / "matplotlib"

_NAPARI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
_NAPARI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

_NAPARI_SETTINGS_FILE = _NAPARI_CONFIG_DIR / "settings.yaml"
_NAPARI_SETTINGS_FILE.touch(exist_ok=True)

os.environ["NAPARI_CONFIG"] = str(_NAPARI_SETTINGS_FILE)
os.environ["MPLCONFIGDIR"] = str(_MPL_CONFIG_DIR)

_original_user_cache_dir = appdirs.user_cache_dir
_original_user_config_dir = appdirs.user_config_dir


def _pytest_user_cache_dir(appname=None, appauthor=None, version=None, opinion=True):
    """Redirect appdirs cache writes into a temporary test directory."""
    return str(_NAPARI_CACHE_DIR)


def _pytest_user_config_dir(appname=None, appauthor=None, version=None, roaming=False):
    """Redirect appdirs config writes into a temporary test directory."""
    return str(_NAPARI_CONFIG_DIR)


appdirs.user_cache_dir = _pytest_user_cache_dir
appdirs.user_config_dir = _pytest_user_config_dir


@pytest.fixture(scope="session", autouse=True)
def _set_qt_api():
    """Ensure a QApplication is available before any test (pytest-qt handles teardown)."""
    # pytest-qt creates a QApplication automatically via the `qtbot` fixture.
    # This fixture is here to document the intent, not to create a second one.
