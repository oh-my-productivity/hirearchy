"""``DerivedQualityReport``: where the stalled states, the held runs, the FAIL counts and the thresholds come from, and what each failure reads."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from hirearchy.budget import BudgetQuery
from hirearchy.kernel import ROOT, JsonObject, Message, OrgError
from hirearchy.mail import MailboxReader
from hirearchy.progress import QualityReport
from hirearchy.progress._ports import ConfigSource, FailCounts, TaskState, TaskStates
from hirearchy.progress._quality import DerivedQualityReport
from hirearchy.progress.testing import FixedConfigSource, FixedFailCounts, ProgressWorld, fs_world
from hirearchy.reflection import ServiceRecord
from hirearchy.reflection.testing import FixedCaseRecords

from ._quality_records import OWNER, case, delivery, record, request


def report(
    w: ProgressWorld, *records: ServiceRecord, fails: FailCounts | None = None, config: ConfigSource | None = None, states: TaskStates | None = None,
    mail: MailboxReader | None = None,
) -> QualityReport:
    return DerivedQualityReport(
        FixedCaseRecords([*records, ServiceRecord("", "", ROOT, "human")]), states or w.states, w.teams, w.tasks, mail or w.mail, w.budget, w.agents,
        fails or FixedFailCounts(), config or FixedConfigSource(),
    )


@pytest.fixture
def w(tmp_path: Path) -> ProgressWorld:
    made = fs_world(tmp_path)
    made.hire(OWNER)
    made.hire("ceo")
    return made


def open_case() -> tuple[ServiceRecord, str]:
    t = request(3)
    c = case([t], state="open")
    return record(cases=[c]), c.id


def test_stalled_comes_from_task_states(w: ProgressWorld) -> None:
    task = w.delegate(ROOT, OWNER, "Memo", 5)
    c = case([task], state="open")
    working = report(w, record(cases=[c]))  # the task is unread in the inbox of `lead`: the team is working on it
    assert "  cases: 1 (done 0, failed 0, blocked 0, open 1 (stalled 0))" in working.quality_text()
    assert working.quality_data()["services"][0]["cases"][0]["stalled"] is False  # type: ignore[index]
    w.begin_run(OWNER)
    w.end_run(OWNER)  # `lead` read it, reported nothing and nothing is running: stalled
    stalled = report(w, record(cases=[c]))
    assert "  cases: 1 (done 0, failed 0, blocked 0, open 1 (stalled 1))" in stalled.quality_text()
    assert stalled.quality_data()["services"][0]["cases"][0]["stalled"] is True  # type: ignore[index]


def test_held_runs_come_from_the_budget(w: ProgressWorld) -> None:
    first = w.delegate(ROOT, "ceo", "Memo", 8)
    w.answer(first, "blocked", "stuck", 0)
    w.delegate(ROOT, "ceo", "Another", 3)  # root moved on without a verdict: the first task is left blocked
    held = w.budget.budget("ceo")
    text = report(w).quality_text()
    assert f"  ceo holds {held} run(s):" in text
    assert f'    task {first.id} from you ("Memo"), blocked ' in text and "left blocked: you have sent ceo 1 task(s) since" in text
    assert report(w).quality_data()["moved_past"][0]["held"] == held  # type: ignore[index]


def test_a_blocked_task_nobody_moved_past_is_not_listed(w: ProgressWorld) -> None:
    first = w.delegate(ROOT, "ceo", "Memo", 8)
    w.answer(first, "blocked", "stuck", 0)
    assert report(w).quality_text().endswith("Blocked tasks moved past without a verdict: none.")


def test_the_cases_line_counts_a_case_whose_latest_task_is_left_blocked(w: ProgressWorld) -> None:
    first = w.delegate(ROOT, OWNER, "Memo", 8)
    w.answer(first, "blocked", "stuck", 0)
    w.delegate(ROOT, OWNER, "Another", 3)
    c = case([first], state="blocked")
    assert "; 1 blocked and moved past without a verdict" in report(w, record(cases=[c])).quality_text()


def test_fails_come_from_the_fail_counts(w: ProgressWorld) -> None:
    t = request(3)
    c = case([t])
    d = delivery(c, 0, result_n=4, signer="lead/checker")
    rec = record(cases=[c], deliveries=(d,))
    text = report(w, rec, fails=FixedFailCounts({"lead/checker": (2, 3)})).quality_text()
    assert "its FAILs before delivery: 2 re-check(s), 3 author rework run(s)" in text
    data = report(w, rec, fails=FixedFailCounts({"lead/checker": (2, 3)})).quality_data()["services"][0]["verifiers"][0]  # type: ignore[index]
    assert (data["rechecks"], data["rework_runs"]) == (2, 3)


def test_an_org_md_that_does_not_parse_gives_the_defaults_and_the_note(w: ProgressWorld) -> None:
    text = report(w, config=FixedConfigSource(error=OrgError("ORG.md cannot be read: bad"))).quality_text()
    lines = text.splitlines()
    assert lines[1].startswith("Thresholds: the defaults (tunable): alarms need 3 judged cases;")
    assert lines[2] == "ORG.md cannot be read (its settings block does not parse): the default thresholds are used."


def test_thresholds_come_from_the_quality_mapping(w: ProgressWorld) -> None:
    config: JsonObject = {"quality": {"min_judged": 5, "cost_ratio": "1.5", "repeat_failures": 9}}
    lines = report(w, config=FixedConfigSource(config)).quality_text().splitlines()
    assert lines[1] == (
        "Thresholds: from ORG.md quality: (tunable): alarms need 5 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.5x its approved runs."
    )
    assert lines[2] == "quality.repeat_failures in ORG.md is not a whole number from 1 to 3: the default 2 is used."
    assert report(w, config=FixedConfigSource(config)).quality_data()["thresholds"]["source"] == "ORG.md"  # type: ignore[index]


class RaisingStates(TaskStates):
    def state_of(self, task: Message, result: Message | None, team: Sequence[str]) -> TaskState:
        raise OrgError("no states today")


class RaisingFails(FailCounts):
    def fails(self, addr: str) -> tuple[int, int]:
        raise OSError("no mailbox")


class RaisingMail:
    """A mailbox reader whose boxes cannot be read (only the reads the report makes)."""

    def received(self, addr: str) -> list[Message]:
        raise OSError("mailbox gone")


class NoBudget(BudgetQuery):
    def budget(self, addr: str) -> int | None:
        raise OrgError("no budget today")

    def delegable(self, addr: str) -> tuple[int, int, int]:
        raise OrgError("no budget today")

    def grant_hint(self, addr: str) -> str:
        raise OrgError("no budget today")


def test_each_auxiliary_error_reads_unknown(w: ProgressWorld) -> None:
    rec, _ = open_case()
    c2 = case([request(9)])
    d = delivery(c2, 0, result_n=10, signer="lead/checker")
    both = record(cases=[*rec.cases, c2], deliveries=(d,))
    text = report(w, both, states=RaisingStates(), fails=RaisingFails()).quality_text()
    assert "open 1 (stalled: unknown (no states today))" in text
    assert "PASS precision n/a (0 of 0); its FAILs before delivery: unknown (no mailbox)" in text
    data = report(w, both, states=RaisingStates(), fails=RaisingFails()).quality_data()["services"][0]  # type: ignore[index]
    assert data["stalled_error"] == "no states today" and data["verifiers"][0]["fails_error"] == "no mailbox"


def test_held_and_mailbox_failures_read_unknown(w: ProgressWorld) -> None:
    first = w.delegate(ROOT, "ceo", "Memo", 8)
    w.answer(first, "blocked", "stuck", 0)
    w.delegate(ROOT, "ceo", "Another", 3)
    empty = FixedCaseRecords([ServiceRecord("", "", ROOT, "human")])
    broken = DerivedQualityReport(empty, w.states, w.teams, w.tasks, w.mail, NoBudget(), w.agents, FixedFailCounts(), FixedConfigSource())
    assert "  ceo holds an unknown number of runs (no budget today):" in broken.quality_text()
    assert broken.quality_data()["moved_past"][0]["held_error"] == "no budget today"  # type: ignore[index]
    unreadable = DerivedQualityReport(empty, w.states, w.teams, w.tasks, cast(MailboxReader, RaisingMail()), w.budget, w.agents, FixedFailCounts(), FixedConfigSource())
    assert "  ceo: blocked tasks cannot be read (mailbox gone)" in unreadable.quality_text()
    assert unreadable.quality_data()["moved_past"][0]["error"] == "mailbox gone"  # type: ignore[index]
