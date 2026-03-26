"""Root conftest.py — sets the QTEXTRAPLOT_PYTEST env var and provides shared fixtures."""

import os

import pytest

# Tell qtextraplot it is running under pytest so test-specific guards activate.
os.environ["QTEXTRAPLOT_PYTEST"] = "1"


@pytest.fixture(scope="session", autouse=True)
def _set_qt_api():
    """Ensure a QApplication is available before any test (pytest-qt handles teardown)."""
    # pytest-qt creates a QApplication automatically via the `qtbot` fixture.
    # This fixture is here to document the intent, not to create a second one.
