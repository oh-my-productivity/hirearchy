"""``HealthReviewPlanner``: who is told what in a review, decided from the health of the agents and from who was told what last time.

The wording is the notices' (``RecordingNotices`` shows which item and which note were asked for, with which arguments)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.health import AgentHealth
from orgmcp.health.testing import FixedHealthAnalyzer
from orgmcp.kernel import ROOT
from orgmcp.kernel.testing import FakeClock
from orgmcp.mail.testing import MemoryMailbox, memory_mailbox
from orgmcp.review._planner import HealthReviewPlanner
from orgmcp.review._ports import ReserveCheck, ReviewPlanner, RunTotal
from orgmcp.review.testing import healthy
from orgmcp.templates.testing import RecordingNotices

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class Refusals(ReserveCheck):
    """Who may not be written to, and why."""

    def __init__(self) -> None:
        self.why: dict[str, str] = {}
        self.asked: list[str] = []

    def why_not(self, manager: str) -> str:
        self.asked.append(manager)
        return self.why.get(manager, "")


class Total(RunTotal):
    def total(self) -> int:
        return 42


class Parts:
    def __init__(self, tmp_path: Path) -> None:
        mail = memory_mailbox(tmp_path)
        box = mail.reader
        assert isinstance(box, MemoryMailbox)
        self.mail = mail
        self.health = FixedHealthAnalyzer(box.agents, FakeClock())
        self.refusals = Refusals()
        self.notices = RecordingNotices()
        self.planner = HealthReviewPlanner(box.agents, self.health, self.refusals, self.notices, Total())
        assert isinstance(self.planner, ReviewPlanner)

    def hire(self, addr: str, *flags: str) -> None:
        self.mail.agent(addr)
        h: AgentHealth = healthy(addr)
        h.flags.update({flag: f"why {flag}" for flag in flags})
        self.health.put(h)


@pytest.fixture
def p(tmp_path: Path) -> Parts:
    made = Parts(tmp_path)
    made.hire("ceo")
    made.hire("ceo/eng", "idle")
    return made


def test_the_review_is_stamped_with_the_time_and_the_runs_so_far(p: Parts) -> None:
    review = p.planner.plan(NOW, {})
    assert (review.at, review.runs, review.flagged) == (NOW, 42, 1)


def test_the_note_of_a_manager_asks_for_the_items_of_its_new_pairs(p: Parts) -> None:
    review = p.planner.plan(NOW, {})
    assert ("review_item", ("ceo/eng", "idle", "why idle", True, None)) in p.notices.calls
    assert ("review_manager", ("ceo", ("review_item: ceo/eng | idle | why idle | True | None",))) in p.notices.calls
    assert review.notes[0].to == "ceo" and review.notes[0].title == "health review: 1 new problem(s)"


def test_a_pair_that_was_told_is_known_and_not_asked_for_again(p: Parts) -> None:
    review = p.planner.plan(NOW, {"ceo": ["ceo/eng:idle"]})
    assert [n.to for n in review.notes] == [ROOT] and review.notified["ceo"] == ["ceo/eng:idle"]
    assert not any(name == "review_manager" for name, _ in p.notices.calls)


def test_root_asks_for_the_items_of_every_flagged_agent_and_acts_on_its_reports_only(p: Parts) -> None:
    p.hire("ops", "stuck")
    p.planner.plan(NOW, {})
    (summary, items, skipped) = [args for name, args in p.notices.calls if name == "review_root"][0]
    assert summary == "3 agents, 2 flagged." and skipped == {}
    assert items == ("review_item: ceo/eng | idle | why idle | False | None", "review_item: ops | stuck | why stuck | True | None")


def test_a_manager_that_cannot_be_written_to_is_skipped_and_listed_for_root(p: Parts) -> None:
    p.refusals.why["ceo"] = "paused"
    review = p.planner.plan(NOW, {})
    assert review.skipped == {"ceo": "paused"} and [n.to for n in review.notes] == [ROOT] and "ceo" not in review.notified
    assert p.refusals.asked == ["ceo"]  # only a manager with news is asked about
    (root_call,) = [args for name, args in p.notices.calls if name == "review_root"]
    assert root_call[2] == {"ceo": "paused"}


def test_nothing_is_decided_about_a_manager_whose_reports_are_well(p: Parts) -> None:
    p.hire("ops")
    p.hire("ops/dev")
    p.planner.plan(NOW, {})
    assert p.refusals.asked == ["ceo"]


def test_an_organization_without_flags_has_no_notes(p: Parts) -> None:
    p.health.put(healthy("ceo/eng"))
    review = p.planner.plan(NOW, {})
    assert review.notes == [] and review.notified == {} and review.flagged == 0
