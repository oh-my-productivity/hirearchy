# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import shutil
import time

import pytest
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, join_frontmatter, split_frontmatter


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()
    return org


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def test_a_message_delivery_with_events_is_not_noticeably_slower(org):
    def timed(n=60):
        start = time.perf_counter()
        for _ in range(n):
            org.send(ROOT, "ceo", "x")
        return time.perf_counter() - start

    configure(org, events=False)
    off = timed()
    configure(org, events=True)
    on = timed()
    assert on < off * 3 + 0.5
