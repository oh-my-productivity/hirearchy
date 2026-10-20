#!/bin/sh
# Everything that must be green before a change is done: the tests (unit, golden, class-interface check), mypy --strict on
# the refactored packages, and the import-linter contracts. Extra arguments go to pytest.
#
#   scripts/check.sh              # all of it
#   scripts/check.sh tests/golden # pytest on a subset, then mypy and lint-imports
#
# tests/architecture/test_static_checks.py would run mypy and lint-imports again inside pytest, so it is deselected here.
set -eu
cd "$(dirname "$0")/.."

uv run pytest -q --deselect tests/architecture/test_static_checks.py "$@"
uv run python scripts/static_checks.py all
