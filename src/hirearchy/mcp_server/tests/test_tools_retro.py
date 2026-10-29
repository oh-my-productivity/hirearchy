"""``retro``: root's tool for the retro brief (design 4.7): root only, the text of the brief, a ``since`` that is a date, a datetime or a message id."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hirearchy.kernel import ROOT, OrgError
from hirearchy.mcp_server._instructions import InstructionText
from hirearchy.mcp_server._tools_retro import RetroTools
from hirearchy.mcp_server.testing import MemoryBinding
from hirearchy.retro import Brief, RetroBriefs, render_brief
from hirearchy.retro.testing import FixedRetroBriefs

from ._support import call, described, fails, serve
from pathlib import Path

HERE = Path("/memory/org")
BRIEF = Brief("B1", datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc), None, "since the organization started", 3, 3)


def tools(briefs: RetroBriefs, *, exists: bool = True) -> RetroTools:
    return RetroTools(InstructionText(MemoryBinding(HERE, exists=exists)), lambda: briefs)


def test_root_retro_returns_the_brief() -> None:
    fixed = FixedRetroBriefs(BRIEF)
    assert call(serve(tools(fixed), ROOT), "retro") == render_brief(BRIEF) and fixed.calls == [None]


def test_an_agents_retro_is_refused_word_for_word() -> None:
    fixed = FixedRetroBriefs(BRIEF)
    for who in ("ceo", "ceo/eng"):
        assert fails(serve(tools(fixed), who), "retro").endswith("refused: retro is root's: it briefs the user. Nothing was read.")
    assert fixed.calls == []


def test_since_takes_a_date_a_datetime_or_a_message_id() -> None:
    fixed = FixedRetroBriefs(BRIEF)
    server = serve(tools(fixed), ROOT)
    call(server, "retro", since="2026-11-02")
    call(server, "retro", since="2026-11-02T10:30:00+00:00")
    call(server, "retro", since="20261102T103000123456-1-ab12")
    assert fixed.calls == [
        datetime(2026, 11, 2).astimezone(), datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc), datetime(2026, 11, 2, 10, 30, 0, 123456, tzinfo=timezone.utc),
    ]
    assert fixed.calls and call(server, "retro", since=" ") and fixed.calls[-1] is None  # a blank since is none


class Future(RetroBriefs):
    def brief(self, *, since: datetime | None = None) -> Brief:
        raise OrgError(f"refused: since is in the future ({since}). Nothing was read.")


def test_a_bad_or_future_since_is_refused() -> None:
    assert fails(serve(tools(FixedRetroBriefs(BRIEF)), ROOT), "retro", since="yesterday").endswith(
        "refused: since must be a date (2026-11-02), a datetime with offset or a message id: yesterday. Nothing was read."
    )
    assert "refused: since is in the future" in fails(serve(tools(Future()), ROOT), "retro", since=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat())


def test_before_an_organization_exists_the_setup_text_answers() -> None:
    assert call(serve(tools(FixedRetroBriefs(BRIEF), exists=False), ROOT), "retro").startswith("Setup: no organization exists")


def test_the_docstring_is_the_design_s() -> None:
    text = " ".join(described(serve(tools(FixedRetroBriefs(BRIEF)), ROOT))["retro"].split())  # (the description keeps the docstring's line breaks)
    assert text.startswith("The retro brief: what the client said, what got past a check, whether past changes held, how the organization changed, the team's own proposals")
    assert "Call it when the user asks, or" in text and "Costs no run." in text and "never add an item of your own" in text


def test_the_docstring_says_offer_then_call_after_the_yes() -> None:
    text = " ".join(described(serve(tools(FixedRetroBriefs(BRIEF)), ROOT))["retro"].split())
    assert "Call it when the user asks, or after their yes to your offer when a reply says one is due. Show the block" in text
