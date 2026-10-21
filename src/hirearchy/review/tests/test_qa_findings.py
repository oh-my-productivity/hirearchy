# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from datetime import timedelta

from testkit import review_world as review
from testkit.reach.hirearchy.core import ROOT, join_frontmatter, split_frontmatter, utcnow

ENG = "ceo/eng"


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def test_qa7_retiring_agents_does_not_postpone_the_next_review(org):
    runs = org.dir(ENG) / "runs"
    for i in range(5):
        (runs / f"20260101T0000000000{i:02d}.log").touch()
    review.review(org, utcnow())  # ledger: 5 runs so far
    org.retire("ceo", "eng", "done")
    ceo_runs = org.dir("ceo") / "runs"
    for i in range(3):  # three new runs since the review
        (ceo_runs / f"20260102T0000000000{i:02d}.log").touch()
    configure(org, review_every_runs=2, review_every_seconds=10**9)
    assert review.review_if_due(org, utcnow()) is not None


def test_qa8_review_does_not_spend_the_reserve_of_a_manager(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=3)
    org.delegate("ceo", ENG, "work", "g", "a", budget=2)  # budget 1 left, one result outstanding (the reserve)
    assert org.budget("ceo") == 1 and len(org.outstanding("ceo")) == 1
    configure(org, health={"idle_after_seconds": -1})  # ops (never used) is idle -> news for ceo
    result = review.review(org, utcnow() + timedelta(hours=1))
    assert not [n for n in result.notes if n.to == "ceo"], "the note's run would consume the run reserved for eng's result"
