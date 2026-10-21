"""Comparing a text with a file of ``expected/`` (captured from the flat ``cli.py``; never rewritten by a test)."""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

EXPECTED = Path(__file__).with_name("expected")


def check(name: str, actual: str) -> None:
    path = EXPECTED / name
    if not path.is_file():
        pytest.fail(f"no expected text {path.relative_to(EXPECTED.parent)}")
    expected = path.read_bytes()
    if expected != actual.encode("utf-8"):
        diff = "".join(difflib.unified_diff(expected.decode("utf-8", "replace").splitlines(keepends=True), actual.splitlines(keepends=True),
                                            f"expected/{name}", "actual", n=2))
        pytest.fail(f"{name} differs from what cli.py printed:\n{diff[:6000]}")
