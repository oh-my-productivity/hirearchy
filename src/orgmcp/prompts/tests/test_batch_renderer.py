"""``BatchRenderer``: a message of a batch as it is shown; a result is followed by the task it answers and, when it can be told, the task it serves."""

from __future__ import annotations

import pytest

from orgmcp.kernel import Message
from orgmcp.mail.testing import MemoryMailbox
from orgmcp.prompts._batch import BatchRenderer
from orgmcp.prompts._ports import ContextRenderer, TaskQuoter, UpstreamTasks
from orgmcp.prompts.testing import FixedQuote, FixedUpstream

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def at(n: int, sender: str) -> str:
    return f"20260101T0000000000{n:02d}-{sender}-aaaa"


class Story:
    def __init__(self, quoter: TaskQuoter | None = None, upstream: UpstreamTasks | None = None) -> None:
        self.box = MemoryMailbox()
        self.quote = quoter or FixedQuote()
        self.up = upstream or FixedUpstream()
        self.renderer: ContextRenderer = BatchRenderer(self.box, self.quote, self.up)
        self.sub = Message(sender="ceo", to="ceo/eng", type="task", title="Draft", body="Draft it.", id=at(5, "ceo"))
        self.box.store(self.sub)
        self.result = Message(sender="ceo/eng", to="ceo", type="result", title="Draft", body="ok", id=at(6, "ceo-eng"), reply_to=self.sub.id, status="done")
        self.box.store(self.result)


def test_a_message_that_is_not_a_result_is_its_own_rendering() -> None:
    s = Story()
    note = Message(sender="root", to="ceo", type="note", title="n", body="hello", id=at(1, "root"))
    assert s.renderer.render("ceo", note) == note.render()


def test_a_result_with_no_reply_to_is_its_own_rendering() -> None:
    s = Story()
    loose = Message(sender="ceo/eng", to="ceo", type="result", title="r", body="b", id=at(7, "ceo-eng"))
    assert s.renderer.render("ceo", loose) == loose.render()


def test_a_result_to_a_task_the_agent_did_not_send_is_its_own_rendering() -> None:
    s = Story()
    stray = Message(sender="ceo/eng", to="ceo", type="result", title="r", body="b", id=at(7, "ceo-eng"), reply_to="20260101T000000000009-ceo-bbbb")
    assert s.renderer.render("ceo", stray) == stray.render()


def test_a_result_is_followed_by_the_task_it_answers_quoted() -> None:
    s = Story()
    assert s.renderer.render("ceo", s.result) == (
        f"{s.result.render()}\n[The task you delegated to ceo/eng that this result answers ({s.sub.id}). "
        f"Judge the result against these criteria, verbatim:]\nQUOTE\n"
    )
    assert s.quote.asked == [s.sub]  # type: ignore[attr-defined]


def test_an_open_upstream_task_is_named() -> None:
    mine = Message(sender="root", to="ceo", type="task", title="Strict blurb", body="b", id=at(1, "root"))
    s = Story(upstream=FixedUpstream((mine, None)))
    assert s.renderer.render("ceo", s.result).endswith(
        f'[It was the only task assigned to you before you delegated this, so it probably serves your open task {mine.id} "Strict blurb": '
        "the result must also satisfy that task's criteria (shown in full in this prompt).]\n"
    )


def test_an_upstream_task_reported_blocked_may_be_reported_again() -> None:
    mine = Message(sender="root", to="ceo", type="task", title="Strict blurb", body="b", id=at(1, "root"))
    blocked = Message(sender="ceo", to="root", type="result", title="r", body="b", id=at(2, "ceo"), reply_to=mine.id, status="blocked")
    out = Story(upstream=FixedUpstream((mine, blocked))).renderer.render("ceo", Story().result)
    assert out.endswith(
        f'[It was the only task assigned to you before you delegated this, so it probably serves your task {mine.id} "Strict blurb", which you '
        "already reported blocked. That is not final: you may `report` it again, once, if the blocker is resolved (its criteria are shown in "
        "your state). The new report must meet rule 6: `done` only if every criterion is met and verified by you, including any required review "
        "of the FINAL version, not an earlier draft; otherwise report `blocked` or `failed`. Do not claim in a note that criteria are met.]\n"
    )


def test_an_upstream_task_reported_done_or_failed_is_final() -> None:
    mine = Message(sender="root", to="ceo", type="task", title="Strict blurb", body="b", id=at(1, "root"))
    for status in ("done", "failed"):
        final = Message(sender="ceo", to="root", type="result", title="r", body="b", id=at(2, "ceo"), reply_to=mine.id, status=status)
        out = Story(upstream=FixedUpstream((mine, final))).renderer.render("ceo", Story().result)
        assert out.endswith(
            f'[It was the only task assigned to you before you delegated this, so it probably serves your task {mine.id} "Strict blurb", which you '
            f"already reported {status}: that is final. Do not claim in a note that its criteria are met or try to change its outcome; if you have "
            "information for root, send it as information only, saying what was and was not verified.]\n"
        )


def test_the_upstream_is_asked_about_the_delegation_not_the_result() -> None:
    up = FixedUpstream()
    s = Story(upstream=up)
    s.renderer.render("ceo", s.result)
    assert up.asked == [("ceo", s.sub)]
