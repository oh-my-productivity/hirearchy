"""The expected texts of ``expected/``: captured from the module ``review.py`` (before the package existed) on ``_scenario``'s organization."""

from __future__ import annotations

from pathlib import Path

EXPECTED = Path(__file__).with_name("expected")


def expected(name: str) -> str:
    return (EXPECTED / name).read_text(encoding="utf-8")
