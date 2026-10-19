"""The derived views of a ``Case``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmcp.kernel import Message
from orgmcp.reflection import Case, Verdict

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-reflection")

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def note(kind: str, seconds: int) -> Message:
    return Message(id=f"{(T + timedelta(seconds=seconds)):%Y%m%dT%H%M%S%f}-root-0000", sender="root", to="ceo", type="note", body="b", feedback=kind)


def verdict(kind: str, seconds: int) -> Verdict:
    message = note(kind, seconds)
    return Verdict(kind, "", None, "T", 0, message)


def case(verdicts: list[Verdict], finished: datetime | None = None) -> Case:
    task = Message(sender="root", to="ceo", type="task", body="b", title="The title")
    return Case(
        id="C", service="s", owner="ceo", tasks=[task], result=None, state="done", playbook=0, used=0, reworks=0, budget=5, runs=1, lessons=[],
        verdicts=verdicts, started=None, finished=finished,
    )


def test_the_title_is_that_of_the_first_request() -> None:
    assert case([]).title == "The title"


def test_a_case_nobody_rated_has_no_verdict() -> None:
    c = case([])
    assert (c.verdict, c.feedback, c.rejected, c.accepted_after_reject, c.evidence_at) == (None, None, False, False, None)


def test_the_latest_verdict_is_the_final_one() -> None:
    first, last = verdict("reject", 1), verdict("accept", 2)
    c = case([first, last])
    assert c.verdict == "accept" and c.feedback is last.message and c.rejected and c.accepted_after_reject


def test_an_accept_that_was_never_rejected_is_not_after_a_reject() -> None:
    c = case([verdict("accept", 1)])
    assert c.verdict == "accept" and not c.rejected and not c.accepted_after_reject


def test_a_reject_after_an_accept_is_a_reject() -> None:
    c = case([verdict("accept", 1), verdict("reject", 2)])
    assert c.verdict == "reject" and c.rejected and not c.accepted_after_reject


def test_the_evidence_is_the_latest_of_the_final_result_and_the_final_feedback() -> None:
    later = case([verdict("accept", 100)], finished=T + timedelta(seconds=10))
    assert later.evidence_at == T + timedelta(seconds=100)
    earlier = case([verdict("accept", 5)], finished=T + timedelta(seconds=10))
    assert earlier.evidence_at == T + timedelta(seconds=10)


def test_a_case_that_only_finished_has_its_finish_for_evidence() -> None:
    assert case([], finished=T).evidence_at == T
