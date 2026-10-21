"""Contract of ``HealthReviewer``: the reviewer over an organization on disk and over the in-memory ports tells the same people the same things, keeps the
same ledger and emits the same event.

The health of the agents is what the test puts in (``FixedHealthAnalyzer``), so each case names the flags it is about; the wording of the notes is
``Notices``' (``static_notices``), so a case compares a note with what the notices make of the items it expects."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT
from hirearchy.review import HealthReviewer
from hirearchy.review.testing import IMPLEMENTATIONS, ReviewWorld, later, org_md

from ._support import IDLE, implementations, ledger, ledger_of, staffed, stamp, told


@pytest.fixture(params=implementations(IMPLEMENTATIONS[HealthReviewer]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReviewWorld:
    """An organization without agents, over disk and over memory."""
    made: ReviewWorld = request.param(tmp_path)
    assert isinstance(made.reviewer, HealthReviewer)
    return made


# ------------------------------------------------------------------------------ who hears what


def test_a_healthy_organization_sends_nothing_and_writes_the_ledger(w: ReviewWorld) -> None:
    staffed(w)
    now = later(w, 100)
    result = w.reviewer.review(now)
    assert result.notes == [] and result.flagged == 0 and result.skipped == {} and result.notified == {} and result.runs == 0 and result.at == now
    assert w.delivered() == 0
    assert w.ledger_text() == ledger(now)


def test_an_organization_without_agents_only_updates_the_ledger(w: ReviewWorld) -> None:
    now = later(w, 100)
    assert w.reviewer.review(now).notes == []
    assert w.ledger_text() == ledger(now) and w.delivered() == 0


def test_a_manager_gets_one_note_with_the_reasons_of_its_new_problems(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    (note,) = [m for m in w.notes("ceo")]
    item = w.notices.review_item("ceo/eng", "idle", IDLE)
    assert note.title == "health review: 1 new problem(s)" and note.body == w.notices.review_manager("ceo", [item])
    assert note.sender == "runtime" and note.wake is True  # a note wakes its manager, which costs it a run
    assert w.notes("ceo/eng") == []  # a worker with no team is nobody's manager
    assert result.notified["ceo"] == ["ceo/eng:idle"]
    assert [(n.to, n.title, n.body) for n in result.notes][0] == ("ceo", note.title, note.body)


def test_root_hears_about_every_flagged_agent_in_one_note(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo", "idle", IDLE)
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    (note,) = w.notes(ROOT)
    items = [w.notices.review_item("ceo", "idle", IDLE, act=True), w.notices.review_item("ceo/eng", "idle", IDLE, act=False)]  # root acts on its reports
    assert note.title == "health review: 2 of 2 agents flagged" and note.body == w.notices.review_root("2 agents, 2 flagged.", items, {})
    assert result.notified[ROOT] == ["ceo:idle", "ceo/eng:idle"] and result.flagged == 2
    assert [n.to for n in result.notes] == ["ceo", ROOT]  # the managers in the order of the tree, root last


def test_each_flag_of_an_agent_is_a_problem_of_its_own(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "stuck", "open task is 1h old and nothing is in progress")
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    assert result.notified["ceo"] == ["ceo/eng:stuck", "ceo/eng:idle"]
    assert told(w, "ceo") == ["health review: 2 new problem(s)"]


def test_only_new_pairs_are_sent_and_persistent_ones_are_not_repeated(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    for i in range(4):  # the same problem, review after review: the pair stays known
        w.reviewer.review(later(w, 100 + i))
    assert len(w.notes("ceo")) == 1 and len(w.notes(ROOT)) == 4
    w.hire("ceo/ops", 10)
    w.flag("ceo/ops", "idle", IDLE)
    w.reviewer.review(later(w, 200))
    newest = w.notes("ceo")[-1]
    assert len(w.notes("ceo")) == 2
    assert newest.body == w.notices.review_manager("ceo", [w.notices.review_item("ceo/ops", "idle", IDLE)])


def test_a_problem_that_goes_away_and_returns_is_new_again(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.reviewer.review(later(w, 100))
    w.heal("ceo/eng")
    result = w.reviewer.review(later(w, 200))
    assert result.notified == {} and len(w.notes("ceo")) == 1
    w.flag("ceo/eng", "idle", IDLE)
    w.reviewer.review(later(w, 300))
    assert len(w.notes("ceo")) == 2


def test_root_hears_every_review_even_when_nothing_is_new(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.reviewer.review(later(w, 100))
    w.reviewer.review(later(w, 200))
    first, second = w.notes(ROOT)
    assert first.body == second.body and ledger_of(w)["notified"] == {"ceo": ["ceo/eng:idle"], ROOT: ["ceo/eng:idle"]}


def test_a_problem_of_the_team_of_a_report_is_told_to_the_manager_of_its_lead(w: ReviewWorld) -> None:
    staffed(w)
    w.hire("ceo/cto", 10)
    w.hire("ceo/cto/dev", 10)
    w.flag("ceo/cto/dev", "paused", "paused: failures")
    result = w.reviewer.review(later(w, 100))
    (note,) = w.notes("ceo")
    assert note.body == w.notices.review_manager("ceo", [w.notices.review_item("ceo/cto/dev", "paused", "paused: failures", branch="ceo/cto")])
    assert result.notified["ceo"] == ["ceo/cto:branch:paused"]
    (lead,) = w.notes("ceo/cto")  # the lead hears it directly
    assert lead.body == w.notices.review_manager("ceo/cto", [w.notices.review_item("ceo/cto/dev", "paused", "paused: failures")])


def test_a_team_problem_the_lead_has_itself_is_not_told_twice(w: ReviewWorld) -> None:
    staffed(w)
    w.hire("ceo/cto", 10)
    w.hire("ceo/cto/dev", 10)
    w.flag("ceo/cto", "idle", IDLE)
    w.flag("ceo/cto/dev", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    assert result.notified["ceo"] == ["ceo/cto:idle"]  # the worst flag of the branch is the lead's own: no branch pair


# ------------------------------------------------------------------------------ who cannot be written to


def test_a_paused_manager_is_skipped_but_stays_in_the_summary_of_root(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.pause("ceo", "failures")
    result = w.reviewer.review(later(w, 100))
    assert w.notes("ceo") == [] and result.skipped == {"ceo": "paused"} and "ceo" not in result.notified
    (summary,) = w.notes(ROOT)
    assert summary.body == w.notices.review_root("2 agents, 1 flagged.", [w.notices.review_item("ceo/eng", "idle", IDLE, act=False)], {"ceo": "paused"})
    w.resume("ceo")  # it was never told, so it hears about its report as soon as it can act
    w.reviewer.review(later(w, 200))
    assert len(w.notes("ceo")) == 1


def test_a_manager_without_budget_is_skipped(w: ReviewWorld) -> None:
    staffed(w)
    w.set_budget("ceo", 0)
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    assert result.skipped == {"ceo": "no budget left"} and w.notes("ceo") == []


def test_a_manager_whose_budget_is_reserved_for_its_delegations_is_skipped(w: ReviewWorld) -> None:
    staffed(w)
    w.set_budget("ceo", 1)
    w.delegate("ceo", "ceo/eng")
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    assert result.skipped == {"ceo": "budget 1 is reserved for 1 outstanding delegation(s)"} and w.notes("ceo") == []
    (summary,) = w.notes(ROOT)
    assert "Managers not notified: `ceo` (budget 1 is reserved for 1 outstanding delegation(s))" in summary.body
    w.set_budget("ceo", 3)  # the reserve is covered again: its pending news is delivered now
    w.reviewer.review(later(w, 200))
    assert len(w.notes("ceo")) == 1


def test_a_manager_with_spare_budget_beyond_its_reserve_gets_the_note(w: ReviewWorld) -> None:
    staffed(w)
    w.set_budget("ceo", 2)
    w.delegate("ceo", "ceo/eng")
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100))
    assert result.skipped == {} and len(w.notes("ceo")) == 1


def test_a_skipped_manager_keeps_what_it_already_knew(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.reviewer.review(later(w, 100))
    w.pause("ceo", "failures")
    w.flag("ceo/eng", "stuck", "open task is 1h old and nothing is in progress")
    result = w.reviewer.review(later(w, 200))
    assert result.skipped == {"ceo": "paused"} and result.notified["ceo"] == ["ceo/eng:idle"]  # the new pair is not recorded: it was not told
    assert len(w.notes("ceo")) == 1


# ------------------------------------------------------------------------------ dry run and event


def test_a_dry_run_says_what_it_would_do_and_writes_nothing(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    result = w.reviewer.review(later(w, 100), dry_run=True)
    assert [n.to for n in result.notes] == ["ceo", ROOT] and result.render(dry_run=True).startswith("1 flagged agent(s); would send 2 note(s)")
    assert w.delivered() == 0 and w.ledger_text() is None and w.events.events == []


def test_a_dry_run_leaves_the_ledger_as_it_was(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.put_ledger_text(ledger(later(w, 50), 3, {"ceo": ["ceo/eng:idle"]}))
    before = w.ledger_text()
    result = w.reviewer.review(later(w, 100), dry_run=True)
    assert w.ledger_text() == before and [n.to for n in result.notes] == [ROOT]  # ceo already knows


def test_a_review_emits_one_event_with_the_flagged_count_and_the_recipients(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.reviewer.review(later(w, 100))
    (event,) = w.events.events
    assert event.kind == "review.run" and event.fields == {"flagged": 1, "notes": ["ceo", ROOT]}
    assert event.actor is None and event.run is None and event.trace is None


def test_the_clock_is_the_time_of_a_review_without_one(w: ReviewWorld) -> None:
    staffed(w)
    before = w.clock.t
    result = w.reviewer.review()
    assert before < result.at <= w.clock.t and result.at.tzinfo is not None
    assert ledger_of(w)["at"] == stamp(result.at)


def test_a_naive_time_is_taken_as_utc(w: ReviewWorld) -> None:
    staffed(w)
    result = w.reviewer.review(datetime(2026, 1, 1, 12, 0, 0))
    assert result.at == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc) and ledger_of(w)["at"] == "2026-01-01T12:00:00+00:00"


def test_the_runs_of_the_review_are_the_runs_used_so_far(w: ReviewWorld) -> None:
    staffed(w)
    w.add_runs("ceo", 2)
    w.add_runs("ceo/eng", 3)
    w.add_retired_runs(4)
    assert w.reviewer.review(later(w, 100)).runs == 9 and ledger_of(w)["runs"] == 9


def test_a_damaged_ledger_counts_as_no_one_having_been_told(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.put_ledger_text("[1, 2]")
    w.reviewer.review(later(w, 100))
    assert len(w.notes("ceo")) == 1 and ledger_of(w)["notified"] == {"ceo": ["ceo/eng:idle"], ROOT: ["ceo/eng:idle"]}


# ------------------------------------------------------------------------------ when a review is due


def test_the_first_check_only_starts_the_clock(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.add_runs("ceo", 2)
    now = later(w, 100)
    assert w.reviewer.review_if_due(now) is None
    assert w.ledger_text() == ledger(now, 2) and w.delivered() == 0 and w.events.events == []


def test_a_malformed_ledger_starts_the_clock_again(w: ReviewWorld) -> None:
    staffed(w)
    for raw in ("not json", "[]", "{}", '"text"'):
        w.put_ledger_text(raw)
        now = later(w, 100)
        assert w.reviewer.review_if_due(now) is None and w.ledger_text() == ledger(now), raw


def test_a_review_is_due_after_review_every_runs_across_the_organization(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.configure(org_md(review_every_runs=5, review_every_seconds=10**9))
    w.reviewer.review_if_due(later(w, 100))  # the baseline
    w.add_runs("ceo", 4)
    assert w.reviewer.review_if_due(later(w, 101)) is None
    w.add_runs("ceo/eng", 1)
    assert w.reviewer.total_runs() == 5
    result = w.reviewer.review_if_due(later(w, 102))
    assert result is not None and result.runs == 5 and ledger_of(w)["runs"] == 5
    assert w.reviewer.review_if_due(later(w, 103)) is None  # counts from the last review
    w.add_runs("ceo", 5)
    assert w.reviewer.review_if_due(later(w, 104)) is not None


def test_a_review_is_due_after_review_every_seconds(w: ReviewWorld) -> None:
    staffed(w)
    w.configure(org_md(review_every_seconds=100, review_every_runs=1000))
    w.reviewer.review_if_due(later(w, 0))
    assert w.reviewer.review_if_due(later(w, 99)) is None
    assert w.reviewer.review_if_due(later(w, 100)) is not None
    assert w.reviewer.review_if_due(later(w, 150)) is None  # the clock restarted with that review
    assert w.reviewer.review_if_due(later(w, 200)) is not None


def test_a_ledger_whose_time_cannot_be_read_is_due_by_time(w: ReviewWorld) -> None:
    staffed(w)
    w.configure(org_md(review_every_seconds=10**9, review_every_runs=1000))
    w.put_ledger_text(json.dumps({"at": "yesterday", "runs": 0, "notified": {}}))
    assert w.reviewer.review_if_due(later(w, 100)) is not None
    w.put_ledger_text(json.dumps({"runs": 0, "notified": {}}))
    assert w.reviewer.review_if_due(later(w, 200)) is not None


def test_a_due_review_is_a_review_with_that_time(w: ReviewWorld) -> None:
    staffed(w)
    w.flag("ceo/eng", "idle", IDLE)
    w.configure(org_md(review_every_seconds=10, review_every_runs=1000))
    w.reviewer.review_if_due(later(w, 0))
    result = w.reviewer.review_if_due(later(w, 10))
    assert result is not None and result.at == later(w, 10) and [n.to for n in result.notes] == ["ceo", ROOT]
    assert len(w.notes("ceo")) == 1 and [e.kind for e in w.events.events] == ["review.run"]


def test_a_run_counter_that_shrinks_rebases_the_ledger_and_causes_no_review(w: ReviewWorld) -> None:
    staffed(w)
    w.configure(org_md(review_every_runs=2, review_every_seconds=10**9))
    w.add_runs("ceo", 1)
    w.put_ledger_text(ledger(later(w, 50), 5, {"ceo": ["ceo/eng:idle"]}))  # the run logs vanished some other way: 5 were counted, 1 is left
    assert w.reviewer.review_if_due(later(w, 100)) is None
    assert w.ledger_text() == ledger(later(w, 50), 1, {"ceo": ["ceo/eng:idle"]})  # the time and who was told are kept, the count is what is seen
    w.add_runs("ceo", 2)  # no permanent stall: two more runs make a review due
    assert w.reviewer.review_if_due(later(w, 101)) is not None


def test_the_cadence_comes_from_the_files_not_from_memory(w: ReviewWorld) -> None:
    staffed(w)
    w.configure(org_md(review_every_runs=3, review_every_seconds=10**9))
    w.reviewer.review_if_due(later(w, 0))
    w.add_runs("ceo", 2)
    assert w.reviewer.review_if_due(later(w, 1)) is None
    w.configure(org_md(review_every_runs=2, review_every_seconds=10**9))  # ORG.md is read at each check
    assert w.reviewer.review_if_due(later(w, 2)) is not None


# ------------------------------------------------------------------------------ runs and ledger


def test_the_total_of_runs_counts_every_agent_and_never_goes_down_when_agents_retire(w: ReviewWorld) -> None:
    staffed(w)
    assert w.reviewer.total_runs() == 0
    w.add_runs("ceo", 2)
    w.add_runs("ceo/eng", 3)
    assert w.reviewer.total_runs() == 5
    w.add_retired_runs(4)
    assert w.reviewer.total_runs() == 9


def test_no_ledger_reads_as_none(w: ReviewWorld) -> None:
    assert w.reviewer.read_ledger() is None


def test_a_ledger_reads_as_at_runs_and_notified(w: ReviewWorld) -> None:
    w.put_ledger_text(ledger(later(w, 10), 7, {"ceo": ["ceo/eng:idle"]}))
    assert w.reviewer.read_ledger() == {"at": stamp(later(w, 10)), "runs": 7, "notified": {"ceo": ["ceo/eng:idle"]}}


def test_a_ledger_that_is_not_an_object_or_is_empty_reads_as_none(w: ReviewWorld) -> None:
    for raw in ("not json", "[]", "{}", "3", '"x"', ""):
        w.put_ledger_text(raw)
        assert w.reviewer.read_ledger() is None, raw


def test_the_pieces_of_a_damaged_ledger_are_normalised(w: ReviewWorld) -> None:
    w.put_ledger_text(json.dumps({"at": "x", "runs": True, "notified": {"a": ["k"], "b": "no", "c": 3, "d": []}}))
    assert w.reviewer.read_ledger() == {"at": "x", "runs": 0, "notified": {"a": ["k"], "d": []}}
    w.put_ledger_text(json.dumps({"at": None, "runs": "7", "notified": [1]}))
    assert w.reviewer.read_ledger() == {"at": None, "runs": 0, "notified": {}}
    w.put_ledger_text(json.dumps({"x": 1}))
    assert w.reviewer.read_ledger() == {"at": None, "runs": 0, "notified": {}}
