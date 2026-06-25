# typecheck: run mypy type checking
typecheck:
    uvx mypy

# check-manifest: verify package manifest
check-manifest:
    uvx check-manifest

# dist: build the distribution (depends on check-manifest)
dist: check-manifest
    uv pip install -U build
    python -m build

# pre: run pre-commit hooks
pre:
    prek run

# fmt: format and fix code with ruff
fmt:
    ruff format .
    ruff check . --fix --unsafe-fixes

# watch: watch target with optional arguments
watch *args:
    just {{args}}

# untrack: reset git tracking (often used after .gitignore changes)
untrack:
    git rm -r --cached .
    git add .
    git commit -m ".gitignore fix"
