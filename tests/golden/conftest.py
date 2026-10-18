"""Fixtures of the golden suite (the shared ones are in the root conftest.py)."""

from __future__ import annotations

import pytest
from golden_support import CounterSecrets, FixedClock, make_normalizer, fake_datetime

from orgmcp.core import Org


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """A fixed clock and counter-based message ids for every golden test."""
    c = FixedClock()
    fake = fake_datetime(c)
    for module in ("orgmcp.core", "orgmcp.telemetry", "orgmcp.scheduler"):
        monkeypatch.setattr(f"{module}.datetime", fake)
    monkeypatch.setattr("orgmcp.core.secrets", CounterSecrets())
    return c


@pytest.fixture
def norm(tmp_path, isolated_kiro):
    """``norm(text)``: tmp paths, $HOME, the venv and the project directory replaced by placeholders."""
    n = make_normalizer(tmp_path, isolated_kiro)
    return n


@pytest.fixture
def gorg(tmp_path, norm):
    """An empty organization (default config except a fast poll) at ``<tmp>/org``; its path normalizes to ``<ORG>``."""
    o = Org.init(tmp_path / "org", "Golden mission: ship the thing.", {"poll_seconds": 0.05})
    norm.add(o.root, "<ORG>")
    return o
