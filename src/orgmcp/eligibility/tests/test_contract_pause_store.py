"""Contract of ``PauseStore``: the flag files on disk, the dashboard's caching decorator and the fake keep the same flags and emit the same events.

What the callers rely on: the reason is the text of the flag file, an empty file still means paused, ``resume`` says so in an event only when
there was something to resume, and the events carry who did it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.eligibility import PauseStore
from orgmcp.eligibility.testing import IMPLEMENTATIONS, PauseHarness

from ._support import implementations


@pytest.fixture(params=implementations(IMPLEMENTATIONS[PauseStore]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> PauseHarness:
    made = cast(Callable[[Path], PauseHarness], request.param)(tmp_path)
    assert isinstance(made.store, PauseStore)
    made.agent("ceo")
    made.agent("ceo/eng")
    return made


def kinds(h: PauseHarness) -> list[str]:
    return [e.kind for e in h.events.events]


# ------------------------------------------------------------------------------ paused / pause


def test_an_agent_that_was_never_paused_is_not(h: PauseHarness) -> None:
    assert h.store.paused("ceo") is None and h.flag("ceo") is None


def test_pausing_makes_the_reason_the_state_of_the_flag(h: PauseHarness) -> None:
    h.store.pause("ceo", "failures")
    assert h.store.paused("ceo") == "failures"


def test_the_flag_file_holds_the_reason_exactly_as_given(h: PauseHarness) -> None:
    h.store.pause("ceo", "paused by the user: the demo\nis over")
    assert h.flag("ceo") == "paused by the user: the demo\nis over"


def test_another_agent_is_not_paused(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    assert h.store.paused("ceo/eng") is None and h.flag("ceo/eng") is None


def test_pausing_again_replaces_the_reason(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    h.store.pause("ceo", "failures")
    assert h.store.paused("ceo") == "failures" and h.flag("ceo") == "failures"


def test_an_empty_flag_file_still_means_paused(h: PauseHarness) -> None:
    h.set_flag("ceo", "")
    assert h.store.paused("ceo") == "paused"


def test_a_flag_of_blanks_still_means_paused(h: PauseHarness) -> None:
    h.set_flag("ceo", " \n\t\n")
    assert h.store.paused("ceo") == "paused"


def test_the_reason_read_back_has_no_surrounding_blanks(h: PauseHarness) -> None:
    h.set_flag("ceo", "  failures \n")
    assert h.store.paused("ceo") == "failures"


def test_a_flag_that_is_put_behind_its_back_is_seen(h: PauseHarness) -> None:
    assert h.store.paused("ceo") is None
    h.set_flag("ceo", "set by hand")
    assert h.store.paused("ceo") == "set by hand"


# ------------------------------------------------------------------------------ agent.pause


def test_pausing_emits_agent_pause_with_the_agent_and_the_reason(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    [event] = h.events.events
    assert (event.kind, event.fields) == ("agent.pause", {"agent": "ceo", "reason": "budget"})


def test_the_event_names_who_paused(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget", by="runtime")
    assert h.events.events[0].actor == "runtime"


def test_without_a_name_the_event_leaves_the_actor_to_the_sink(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    assert h.events.events[0].actor is None


def test_a_long_reason_is_cut_in_the_event_and_whole_in_the_flag(h: PauseHarness) -> None:
    reason = "x" * 800
    h.store.pause("ceo", reason)
    assert h.flag("ceo") == reason
    assert h.events.events[0].fields["reason"] == "x" * 499 + "…"


def test_a_reason_of_exactly_the_longest_event_text_is_not_cut(h: PauseHarness) -> None:
    h.store.pause("ceo", "y" * 500)
    assert h.events.events[0].fields["reason"] == "y" * 500


# ------------------------------------------------------------------------------ resume


def test_resuming_removes_the_pause(h: PauseHarness) -> None:
    h.store.pause("ceo", "failures")
    h.store.resume("ceo")
    assert h.store.paused("ceo") is None and h.flag("ceo") is None


def test_resuming_one_agent_leaves_the_others_paused(h: PauseHarness) -> None:
    h.store.pause("ceo", "failures")
    h.store.pause("ceo/eng", "budget")
    h.store.resume("ceo")
    assert h.store.paused("ceo/eng") == "budget"


def test_resuming_emits_agent_resume_with_what_it_was_paused_for(h: PauseHarness) -> None:
    h.store.pause("ceo", "failures")
    h.events.events.clear()
    h.store.resume("ceo", by="human")
    [event] = h.events.events
    assert (event.kind, event.actor) == ("agent.resume", "human")
    assert event.fields == {"agent": "ceo", "reason": "resumed", "previous": "failures"}


def test_the_reason_of_a_resume_is_the_one_given(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    h.events.events.clear()
    h.store.resume("ceo", "budget is back", by="runtime")
    assert h.events.events[0].fields["reason"] == "budget is back"


def test_resuming_an_agent_that_is_not_paused_emits_nothing(h: PauseHarness) -> None:
    h.store.resume("ceo", "just in case", by="human")
    assert h.events.events == [] and h.store.paused("ceo") is None


def test_resuming_twice_emits_one_event(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    h.store.resume("ceo")
    h.store.resume("ceo")
    assert kinds(h) == ["agent.pause", "agent.resume"]


def test_an_empty_flag_resumes_as_paused(h: PauseHarness) -> None:
    h.set_flag("ceo", "")
    h.store.resume("ceo")
    assert h.events.events[0].fields["previous"] == "paused"


def test_the_event_cuts_a_long_previous_reason_at_200(h: PauseHarness) -> None:
    h.store.pause("ceo", "z" * 300)
    h.store.resume("ceo")
    assert h.events.events[1].fields["previous"] == "z" * 199 + "…"


def test_a_pause_after_a_resume_is_a_pause_again(h: PauseHarness) -> None:
    h.store.pause("ceo", "budget")
    h.store.resume("ceo")
    h.store.pause("ceo", "failures")
    assert h.store.paused("ceo") == "failures" and kinds(h) == ["agent.pause", "agent.resume", "agent.pause"]
