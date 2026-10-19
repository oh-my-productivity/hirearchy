"""Helpers shared by the tests of ``review`` (no test lives here)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from orgmcp.review.testing import ReviewWorld

IDLE = "no open tasks and no activity for 5h; candidate to retire"  # the reason of an idle flag, as the analyzer words it

__all__ = ["IDLE", "implementations", "ledger", "ledger_of", "staffed", "stamp", "told"]


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]


def staffed(w: ReviewWorld, budget: int = 10) -> ReviewWorld:
    """``ceo`` (a manager) and ``ceo/eng`` (its report), both with this many runs left and nothing to report."""
    w.hire("ceo", budget)
    w.hire("ceo/eng", budget)
    return w


def stamp(when: datetime) -> str:
    """The time as the ledger writes it."""
    return when.isoformat(timespec="seconds")


def ledger(at: datetime, runs: int = 0, notified: dict[str, list[str]] | None = None) -> str:
    """The text of a ledger, byte for byte as the reviewer writes it."""
    return json.dumps({"at": stamp(at), "runs": runs, "notified": notified or {}}, indent=2) + "\n"


def ledger_of(w: ReviewWorld) -> dict[str, object]:
    text = w.ledger_text()
    assert text is not None
    loaded: dict[str, object] = json.loads(text)
    return loaded


def told(w: ReviewWorld, addr: str) -> list[str]:
    """The titles of the review notes ``addr`` has received."""
    return [m.title for m in w.notes(addr) if m.title.startswith("health review")]

