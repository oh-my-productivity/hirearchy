"""``NoteTools``: send (with the hint on a grant) and reclaim (with the budget left unless root)."""

from __future__ import annotations

from hirearchy.kernel import ROOT
from hirearchy.mcp_server._tools_notes import NoteTools
from hirearchy.mcp_server.testing import HeldBudgets, ScriptedReclaimer, ScriptedSender

from ._support import call, serve


def tools(hints: dict[str, str] | None = None) -> tuple[NoteTools, ScriptedSender, ScriptedReclaimer]:
    sender, reclaimer = ScriptedSender(), ScriptedReclaimer()
    return NoteTools(lambda: sender, lambda: HeldBudgets({"ceo": 5}, hints), lambda: reclaimer), sender, reclaimer


def test_send_says_what_was_sent_where() -> None:
    group, sender, _ = tools()
    assert call(serve(group, "ceo"), "send", to="ceo/eng", body="hello", title="t") == "sent note-1 to ceo/eng"
    assert sender.log.of("send")[0][0][:3] == ("ceo", "ceo/eng", "hello") and sender.log.of("send")[0][1]["title"] == "t"


def test_send_defaults_are_a_plain_note_without_budget() -> None:
    group, sender, _ = tools()
    call(serve(group, "ceo"), "send", to="ceo/eng", body="hello")
    kwargs = sender.log.of("send")[0][1]
    assert (kwargs["type"], kwargs["title"], kwargs["reply_to"], kwargs["budget"], kwargs["wake"]) == ("note", "", None, 0, True)


def test_send_with_budget_to_a_report_adds_what_it_can_do_with_it() -> None:
    group, _, _ = tools({"ceo/eng": "It can hire."})
    out = call(serve(group, "ceo"), "send", to="ceo/eng", body="runs", budget=2)
    assert out == "sent note-1 to ceo/eng with 2 run(s) of budget. It can hire."


def test_send_with_budget_to_anyone_else_adds_no_hint() -> None:
    group, _, _ = tools({"ceo": "never", "ceo/eng": "never"})
    assert call(serve(group, "ceo/eng"), "send", to="ceo", body="back", budget=1) == "sent note-1 to ceo with 1 run(s) of budget"


def test_reclaim_says_what_came_back_and_the_budget_left() -> None:
    group, _, reclaimer = tools()
    out = call(serve(group, "ceo"), "reclaim", report="eng", budget=2)
    assert out == "reclaimed 2 run(s) from eng. Your budget is now 5."
    assert reclaimer.log.of("reclaim") == [(("ceo", "eng", 2), {})]


def test_root_has_no_budget_to_report() -> None:
    group, _, _ = tools()
    assert call(serve(group, ROOT), "reclaim", report="ceo") == "reclaimed 7 run(s) from ceo."
