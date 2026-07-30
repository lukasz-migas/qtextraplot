"""Shared pytest configuration for qtextraplot."""

import os
import tempfile
from pathlib import Path

import appdirs
import platformdirs
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

if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    # macOS can report a zero-sized physical display to Vispy in headless mode.
    try:
        import vispy
    except ImportError:
        pass
    else:
        vispy.config["dpi"] = 96

_original_user_cache_dir = appdirs.user_cache_dir
_original_user_config_dir = appdirs.user_config_dir
_original_platform_user_cache_dir = platformdirs.user_cache_dir
_original_platform_user_config_dir = platformdirs.user_config_dir
_original_platform_user_data_dir = platformdirs.user_data_dir
_original_platform_user_log_dir = platformdirs.user_log_dir
_original_platform_user_state_dir = platformdirs.user_state_dir


def _pytest_user_cache_dir(appname=None, appauthor=None, version=None, opinion=True):
    """Redirect appdirs cache writes into a temporary test directory."""
    return str(_NAPARI_CACHE_DIR)


def _pytest_user_config_dir(appname=None, appauthor=None, version=None, roaming=False):
    """Redirect appdirs config writes into a temporary test directory."""
    return str(_NAPARI_CONFIG_DIR)


appdirs.user_cache_dir = _pytest_user_cache_dir
appdirs.user_config_dir = _pytest_user_config_dir
platformdirs.user_cache_dir = _pytest_user_cache_dir
platformdirs.user_config_dir = _pytest_user_config_dir
platformdirs.user_data_dir = _pytest_user_config_dir
platformdirs.user_log_dir = _pytest_user_config_dir
platformdirs.user_state_dir = _pytest_user_config_dir

# qtextra may be imported by the test environment before this conftest. Keep
# its module-level paths inside the same disposable directory in either case.
from qtextra.utils import appdirs as qtextra_appdirs  # noqa: E402

qtextra_appdirs.USER_DATA_DIR = _NAPARI_CONFIG_DIR
qtextra_appdirs.USER_CACHE_DIR = _NAPARI_CACHE_DIR
qtextra_appdirs.USER_CONFIG_DIR = _NAPARI_CONFIG_DIR / "qtextra-config"
qtextra_appdirs.USER_LOG_DIR = _NAPARI_CONFIG_DIR / "qtextra-logs"
qtextra_appdirs.USER_THEME_DIR = _NAPARI_CONFIG_DIR / "qtextra-themes"
for _path in (
    qtextra_appdirs.USER_CACHE_DIR,
    qtextra_appdirs.USER_CONFIG_DIR,
    qtextra_appdirs.USER_LOG_DIR,
    qtextra_appdirs.USER_THEME_DIR,
):
    _path.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _set_qt_api():
    """Ensure a QApplication is available before any test (pytest-qt handles teardown)."""
    # pytest-qt creates a QApplication automatically via the `qtbot` fixture.
    # This fixture is here to document the intent, not to create a second one.


@pytest.fixture
def _mock_opengl_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid querying an unavailable OpenGL context in headless widget tests."""

    def texture_sizes() -> tuple[int, int]:
        return 4096, 4096

    monkeypatch.setattr(
        "napari._vispy.canvas.get_max_texture_sizes",
        texture_sizes,
    )
    monkeypatch.setattr(
        "napari._vispy.layers.base.get_max_texture_sizes",
        texture_sizes,
    )
    monkeypatch.setattr(
        "napari._vispy.layers.image.get_max_texture_sizes",
        texture_sizes,
    )
    monkeypatch.setattr(
        "napari._vispy.layers.image.get_gl_extensions",
        lambda: "texture_float",
    )
    monkeypatch.setattr(
        "napari_plot._vispy.canvas.get_max_texture_sizes",
        texture_sizes,
    )
