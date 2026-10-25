# mypy: ignore-errors
"""Phase 0b, the cost check on the corpora that kept no run log (design 19.4 as amended by plan commit 1 and the manager's approval of 2026-10-25).

E, E2 and A5 kept no run log, so their runs are checked with ``over_cost(case, approved, ratio)``, the per-case predicate the cost alarm applies, over
``Case`` values that carry the published run counts as the user's runs (none of their reworks is relayed: their tier was never recorded, so every task of
the chain is the user's) and, as ``approved``, ``user_approved(case, budget)`` of the case that ``CaseHistory.chains(runs=False)`` builds from the kept
messages. The alarm's own state on the files is the one 19.3 states and is checked here too.

**Assumption, stated once for the three tests.** With no run log, the runs before each hand-down are read as 0 (``runs=False``), so ``user_ceiling`` is
the hand-downs less what came back, never more: ``user_approved`` is a lower bound, and an overrun is read as more likely, never less. The rows below are
therefore the strictest reading these files allow, and still none is over. No replay of the files fires the alarm (19.3 E3-9 adds a constructed variant).

Each expectation was written from the design's text before it ran. A figure that differs stops the FEAT; it is never edited to match."""

import dataclasses
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

import pytest
from testkit.org_replay import materialize

from hirearchy.core import Org
from hirearchy.reflection import over_cost, user_approved, user_cost

RATIO = Fraction("1.25")  # the default cost_ratio


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def two_decimals(cost: int, approved: int) -> str:
    return str((Decimal(cost) / Decimal(approved)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def rows(cases, published: list[int], budget: int) -> list[tuple[str, int, int, str, bool]]:
    """``(case, the user's runs, the user's approved runs, ratio, over)`` of each case, with its published run count as its (user's) runs."""
    assert len(cases) == len(published)
    found = []
    for case, runs in zip(cases, published, strict=True):
        assert case.runs == 0 and case.runs_unknown == "" and case.relayed_runs == 0  # `chains(runs=False)`: nothing read from a run log
        counted = dataclasses.replace(case, runs=runs)
        approved = user_approved(counted, budget)
        found.append((case.id.rsplit("-", 1)[1], user_cost(counted), approved, two_decimals(user_cost(counted), approved), over_cost(counted, approved, RATIO)))
    return found


def test_e_published_counts(tmp_path):
    """E (`studies/E-service-reflection/STUDY.md` line 22, focus item (c): "R1 8 of 12; R2 17 (12 + 5 rework + 3 + 1 granted = 21 handed out); R3 10 of
    12"; contract budget 12): R1 8 of 12 (0.67x), R2 17 of 17 (1.00x), R3 (blocked, 10 used, 2 still out) 12 of 12 (1.00x): none over. Before D-E5-6 R2 read
    17 > 15, 1.42x: the user's top-ups are what the user approved."""
    org = Org(materialize("E", tmp_path))
    cases = org.runtime.case_history.chains("lead", "weekly-memo", since=None, runs=False)
    assert rows(cases, [8, 17, 10], 12) == [
        ("b495", 8, 12, "0.67", False), ("c686", 17, 17, "1.00", False), ("2c75", 12, 12, "1.00", False),
    ]
    assert over_cost(dataclasses.replace(cases[1], runs=17), 12, RATIO)  # against the contract's 12 alone, 17 > 15: the old reading (1.42x)
    text = org.runtime.quality_report.quality_text()
    assert "    cost: n/a (1 of 3 judged cases); skipped: 20261018T021644679563-root-b495 (runs not counted)" in text.splitlines()


def test_e2_published_counts(tmp_path):
    """E2 (`studies/E2-service-reflection-regression/evidence/run-counts.txt` line 6: "per memo chain (by task time): R1 first pass 9, rework1 5, rework2
    5 = 19; R2 5; R3 first pass 6, rework 5 = 11"; contract budget 15): R1 19 of 20 (0.95x), R2 5 of 15 (0.33x), R3 11 of 15 (0.73x): none over. Before
    D-E5-6 R1 read 19 > 18.75, 1.27x."""
    org = Org(materialize("E2", tmp_path))
    cases = org.runtime.case_history.chains("lead", "meeting-memo", since=None, runs=False)
    assert rows(cases, [19, 5, 11], 15) == [
        ("d22b", 19, 20, "0.95", False), ("55ff", 5, 15, "0.33", False), ("e29b", 11, 15, "0.73", False),
    ]
    assert over_cost(dataclasses.replace(cases[0], runs=19), 15, RATIO)  # against the contract's 15 alone, 19 > 18.75: the old reading (1.27x)
    text = org.runtime.quality_report.quality_text()
    assert (
        "    cost: n/a (0 of 0 cases compared); skipped: 20261018T034955412135-root-d22b, 20261018T040120119761-root-55ff, "
        "20261018T040509774983-root-e29b (runs not counted)"
    ) in text.splitlines()


def test_a5_published_counts(tmp_path):
    """A5 (`studies/A5-research-final3/evidence/run-counts.txt` lines 2-5: "lead 13, lead/researcher 1, lead/writer 4, lead/factcheck 4" = 22; the head
    task's budget 22): 22 of 26 (0.85x): not over (before: 22 of 22, 1.00x)."""
    org = Org(materialize("A5", tmp_path))
    cases = org.runtime.case_history.one_off_cases(runs=False)
    (head,) = cases
    assert head.tasks[0].budget == 22
    assert rows(cases, [22], 22) == [("f768", 22, 26, "0.85", False)]
    assert not over_cost(dataclasses.replace(head, runs=22), 22, RATIO)  # against the head task's budget alone: 1.00x
    text = org.runtime.quality_report.quality_text()
    assert "    cost: n/a (0 of 3 judged cases); skipped: 20261017T214038108044-root-f768 (runs not counted)" in text.splitlines()
