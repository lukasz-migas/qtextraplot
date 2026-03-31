def running_under_pytest() -> bool:
    """Return True if currently running under pytest.

    Set the environment variable ``QTEXTRAPLOT_PYTEST=1`` in your
    ``conftest.py`` to activate test-specific behaviour inside the library.
    """
    import os

    return bool(os.environ.get("QTEXTRAPLOT_PYTEST"))
