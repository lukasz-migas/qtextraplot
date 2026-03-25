# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in development mode
pip install -e .[dev]

# Run tests
pytest --color=yes -v

# Run tests with coverage
pytest --color=yes --cov=qtextraplot --cov-report=xml -v

# Run a single test file
pytest tests/test_foo.py -v

# Run a single test
pytest tests/test_foo.py::test_name -v

# Lint (ruff is configured in pyproject.toml)
ruff check src/

# Format
ruff format src/

# Type check
mypy src/

# Pre-commit (runs absolufy-imports, pycln, black, ruff)
pre-commit run --all-files
```

## Architecture

The package provides Qt widgets for advanced plotting with three visualization backends:

### Backend Layers

**`_napari/`** — Primary backend. Wraps `napari` and `napari-plot` for 1D/2D visualization as Qt widgets. Custom layer types (line, image) are registered dynamically via `_register.py`. The `ViewerBase` in `_wrapper.py` is the abstract base all napari viewer implementations inherit from. `_qt_viewer.py` provides the Qt widget that embeds a vispy canvas. Custom vispy overlays (colorbars, crosshairs, gridlines) live in `_napari/_vispy/overlays/`.

**`_vispy/`** — GPU-accelerated standalone plotting via `vispy.SceneCanvas`. `base.py` provides `BasePlot` with a `BoxZoomCameraMixin` (`camera.py`) for zoom/pan interaction. Used independently from napari for simpler cases.

**`_mpl/`** — Matplotlib-based plotting as QWidget. `plot_base.py` is `PlotBase`, the root class. Has its own toolbar (`toolbar.py`), interaction handlers, and GID constants for identifying plot elements.

### Shared Infrastructure

- **`utils/views_base.py`** — `ViewBase` mixin: shared functionality across all backends (save plot, style updates).
- **`mixins.py`** — `NapariMixin`: provides `_register_views()` and `_update_after_activate()` hooks for viewer subclasses.
- **`config/theme.py`** — Canvas theme definitions applied to all backends.
- **`utils/colormap.py`** — Colormap utilities bridging vispy and napari colormaps.

### Qt Abstraction

All Qt imports go through `qtpy`, which abstracts PyQt5/PyQt6/PySide2/PySide6. The CI tests against PySide6 and PyQt6 on macOS/Windows/Ubuntu.

### Optional Features

The package uses optional dependency groups:
- `[1d]` — `napari-plot` for 1D line plotting
- `[2d]` — `napari` for 2D image layers
- `[mpl]` — `matplotlib` for the `_mpl/` backend
- `[ndv]` — `ndv[vispy]` for NDV viewer integration

Code guarded by these optional imports should handle `ImportError` gracefully.
