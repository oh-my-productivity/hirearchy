"""``CaseTaskLines``: the line of a root task, from the parts it is made of; ``artifacts_of`` and ``rated``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmcp.kernel import ROOT, Message
from orgmcp.progress._lines import CaseTaskLines, artifacts_of, rated
from orgmcp.progress._ports import TaskLines
from orgmcp.progress._counts import LogRunCounts
from orgmcp.progress._states import MailTaskStates
from orgmcp.progress._teams import AgentTaskTeams
from orgmcp.progress.testing import FixedCaseTotals, FixedTeamActivity, ProgressWorld
from orgmcp.reflection import Case, Verdict
from orgmcp.reflection.testing import FixedCaseHistory

from ._support import XFAIL


NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def lines(
    w: ProgressWorld, activity: FixedTeamActivity | None = None, history: FixedCaseHistory | None = None, totals: FixedCaseTotals | None = None,
) -> CaseTaskLines:
    return CaseTaskLines(
        AgentTaskTeams(w.agents), MailTaskStates(w.mail, w.pauses, w.tasks), LogRunCounts(w.mail, w.runs), activity or w.activity,
        history or w.history, totals or w.totals,
    )


def case(tasks: list[Message], verdicts: list[Verdict] | None = None, reworks: int = 0) -> Case:
    return Case(
        id=tasks[0].id, service="brief", owner="ceo", tasks=tasks, result=None, state="done", playbook=1, used=1, reworks=reworks, budget=0, runs=0,
        lessons=[], verdicts=verdicts or [], started=None, finished=None,
    )


def verdict(step: int, task: Message) -> Verdict:
    return Verdict("accept", "", None, task.id, step, task)


def test_it_is_a_task_lines(w: ProgressWorld) -> None:
    assert isinstance(lines(w), TaskLines)


@XFAIL
def test_a_line_is_the_title_the_state_the_runs_and_the_id(w: ProgressWorld, task: Message) -> None:
    assert lines(w).line(task, None, NOW) == f'"Write the report": working. unread work: ceo. runs 0 of 8. (task {task.id})'


@XFAIL
def test_the_last_activity_is_how_long_ago(w: ProgressWorld, task: Message) -> None:
    ago = FixedTeamActivity({"ceo": NOW - timedelta(minutes=7)})
    assert ". last activity 7m ago. " in lines(w, ago).line(task, None, NOW)
    assert "last activity" not in lines(w, FixedTeamActivity({"ceo": NOW + timedelta(minutes=7)})).line(task, None, NOW).replace("0s ago", "")


@XFAIL
def test_a_finished_task_lists_its_artifacts_or_says_there_are_none(w: ProgressWorld, task: Message) -> None:
    done = w.answer(task, "done", "## Summary\nok\n\n## Artifacts\n- a/b.md (3 words)\n* c.md", 0)
    assert ". artifacts: a/b.md, c.md. " in lines(w).line(task, done, NOW)
    failed = w.answer(task, "failed", "no", 0)
    assert ". no artifacts. " in lines(w).line(task, failed, NOW)
    blocked = w.answer(task, "blocked", "no", 0)
    assert "artifacts" not in lines(w).line(task, blocked, NOW)


def request(w: ProgressWorld, title: str = "brief: ai", playbook: int | None = 2) -> Message:
    """A request for the service ``brief`` of ``ceo`` (the delivered task, marked as one)."""
    made = w.delegate(ROOT, "ceo", title, 5)
    made.service, made.playbook = "brief", playbook
    return made


@XFAIL
def test_a_service_request_carries_its_tag_and_the_version_of_the_playbook(w: ProgressWorld) -> None:
    assert lines(w).line(request(w), None, NOW).startswith('"brief: ai" [service brief v2]: working.')
    assert lines(w).line(request(w, playbook=None), None, NOW).startswith('"brief: ai" [service brief v0]: working.')


@XFAIL
def test_a_delivered_request_asks_for_feedback_until_the_client_gives_it(w: ProgressWorld) -> None:
    first = request(w)
    done = w.answer(first, "done", "ok", 0)
    assert ". no feedback yet. " not in lines(w).line(first, None, NOW)
    assert ". no feedback yet. " in lines(w).line(first, done, NOW)
    rated_case = FixedCaseHistory([case([first], [verdict(0, first)])])
    assert "no feedback yet" not in lines(w, history=rated_case).line(first, done, NOW)


@XFAIL
def test_a_rework_chain_adds_the_total_of_the_case_without_a_dangling_full_stop(w: ProgressWorld) -> None:
    first, second = request(w), request(w, "brief: ai again")
    total = "case total: 5 runs used of 16 handed down (contract: 10 per request)."
    chain = FixedCaseHistory([case([first, second], reworks=1)])
    out = lines(w, history=chain, totals=FixedCaseTotals({first.id: total})).line(first, None, NOW)
    assert f". {total} (task {first.id})" in out and ".." not in out
    single = FixedCaseHistory([case([first], reworks=0)])
    assert "case total" not in lines(w, history=single, totals=FixedCaseTotals({first.id: total})).line(first, None, NOW)


@XFAIL
def test_artifacts_of_drops_the_word_counts_and_the_bullets() -> None:
    result = Message(sender="ceo", to=ROOT, type="result", body="## Summary\nx\n## Artifacts\n- ceo/a.md (12 words)\n\n* ceo/b.md\n## Lessons\n- not me")
    assert artifacts_of(result) == ["ceo/a.md", "ceo/b.md"]
    assert artifacts_of(Message(sender="ceo", to=ROOT, type="result", body="no sections")) == []


@pytest.mark.parametrize(("step_of_verdicts", "expected"), [([], False), ([0], True), ([1], True), ([2], True)])
@XFAIL
def test_a_delivery_is_rated_by_a_verdict_on_it_or_on_a_later_rework(step_of_verdicts: list[int], expected: bool) -> None:
    first, second = Message(sender=ROOT, to="ceo", type="task", title="a", body="", id="1"), Message(sender=ROOT, to="ceo", type="task", title="b", body="", id="2")
    found = case([first, second], [verdict(s, [first, second][min(s, 1)]) for s in step_of_verdicts], reworks=1)
    assert rated(found, second) is (bool(step_of_verdicts) and max(step_of_verdicts) >= 1)
    assert rated(found, first) is expected
    assert rated(None, first) is False
