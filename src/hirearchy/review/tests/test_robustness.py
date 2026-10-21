# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
from datetime import timedelta

from testkit.health_world import Scheduler
from testkit.reach.hirearchy.core import ROOT, join_frontmatter, split_frontmatter, utcnow
from testkit.review_world import review_if_due, total_runs


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def write_ledger(org, name, text):
    (org.root / ".runtime").mkdir(exist_ok=True)
    (org.root / ".runtime" / f"{name}.json").write_text(text)


def test_malformed_reviews_ledger_restarts_the_review_clock(org):
    write_ledger(org, "reviews", '{"at": 5, "runs": "x", "notified": [1]}')
    sched = Scheduler(org, echo=lambda _: None)
    sched.tick()
    assert json.loads((org.root / ".runtime" / "reviews.json").read_text())["at"]  # a real timestamp again


def add_runs(org, addr, n, prefix="2026"):
    d = org.dir(addr) / "runs"
    start = len(list(d.glob("*.log")))
    for i in range(n):
        (d / f"{prefix}0101T{start + i:012d}.log").touch()


def test_total_runs_never_goes_down_when_agents_are_retired(org):
    org.hire("ceo", "sub", "S", "s")  # a sub-team: ceo/sub
    add_runs(org, "ceo", 2)
    add_runs(org, "ceo/eng", 3)
    add_runs(org, "ceo/sub", 4)
    assert total_runs(org) == 9
    org.retire("ceo", "eng", "done")
    assert total_runs(org) == 9
    org.retire(ROOT, "ceo", "restructure")  # takes the whole team (ceo, ceo/sub) along
    assert total_runs(org) == 9
    # unrelated files inside a retired directory are not run logs
    for d in (org.root / ".retired").glob("ceo-*"):
        (d / "work" / "runs").mkdir(parents=True, exist_ok=True)
        (d / "work" / "runs" / "x.log").touch()
        (d / "inbox" / "y.log").touch()
    assert total_runs(org) == 9


def test_review_baseline_is_rebased_if_the_counter_ever_shrinks(org):
    configure(org, review_every_runs=2, review_every_seconds=10**9)
    add_runs(org, "ceo", 5)
    review_if_due(org, utcnow())  # starts the clock at 5
    for f in (org.dir("ceo") / "runs").glob("*.log"):
        f.unlink()
    assert review_if_due(org, utcnow()) is None  # no spurious review, and no permanent stall:
    add_runs(org, "ceo", 2, prefix="2027")
    assert review_if_due(org, utcnow()) is not None


# ------------------------------------------------ QA-8: reviews and the reserve
def test_manager_with_spare_budget_beyond_its_reserve_still_gets_the_note(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=4)
    org.delegate("ceo", "ceo/eng", "work", "g", "a", budget=1)  # budget 2 left, one outstanding
    configure(org, health={"idle_after_seconds": -1})
    from testkit.review_world import review

    result = review(org, utcnow() + timedelta(hours=1))
    assert [n.to for n in result.notes if n.to == "ceo"] == ["ceo"] and "ceo" not in result.skipped


def test_skipped_manager_is_listed_in_roots_summary_and_told_later(org):
    from testkit.review_world import review

    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.delegate("ceo", "ceo/eng", "work", "g", "a", budget=2)
    configure(org, health={"idle_after_seconds": -1})
    later = utcnow() + timedelta(hours=1)
    result = review(org, later)
    assert "reserved for 1 outstanding" in result.skipped["ceo"]
    root_note = next(n for n in result.notes if n.to == ROOT)
    assert "Managers not notified: `ceo` (budget 1 is reserved for 1 outstanding delegation(s))" in root_note.body
    org.send(ROOT, "ceo", "more budget", budget=3)  # the reserve is covered again
    again = review(org, later + timedelta(hours=1))
    assert [n.to for n in again.notes if n.to == "ceo"] == ["ceo"]  # its pending news is delivered now
