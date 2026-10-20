"""Fixtures of the golden suite (the shared ones are in the root conftest.py)."""

from __future__ import annotations

import pytest
from golden_support import FixedClock, make_normalizer
from testkit.clocks import clock_ports

from orgmcp.core import Org
from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import CounterTokens


@pytest.fixture(autouse=True)
def clock(process_overrides):
    """A fixed clock and counter-based message ids for every runtime opened during a golden test (``wiring.overriding``)."""
    c = FixedClock()
    process_overrides({**clock_ports(lambda: c.now, events=True), TokenSource: CounterTokens(per_length=True)})
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
