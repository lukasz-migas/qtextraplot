def running_under_pytest() -> bool:
    """Return True if currently running under py.test.

    This function is used to do some adjustment for testing. The environment
    variable ORIGAMI_PYTEST is defined in conftest.py.
    """
    import os

    return bool(os.environ.get("QTEXTRAPLOT_PYTEST"))
