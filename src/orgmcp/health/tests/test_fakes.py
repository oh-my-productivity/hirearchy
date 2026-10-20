"""The fakes of ``testing.py`` that the analyzer's memory world is made of: what each answers is pinned here, apart from the suites that use them."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.eligibility.testing import memory_pauses
from orgmcp.health._ports import CharterStamp
from orgmcp.health.testing import MemoryCharterStamps, StateWords
from orgmcp.kernel import Message
from orgmcp.mail.testing import memory_mailbox

WRITTEN = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


def test_the_memory_stamps_know_only_the_agents_they_were_told_of() -> None:
    stamps = MemoryCharterStamps()
    assert isinstance(stamps, CharterStamp)
    with pytest.raises(FileNotFoundError):
        stamps.modified("ceo")
    stamps.times["ceo"] = WRITTEN
    assert stamps.modified("ceo") == WRITTEN


def test_the_state_words_follow_the_precedence_running_paused_pending_idle(tmp_path: Path) -> None:
    mail, pauses = memory_mailbox(tmp_path), memory_pauses(tmp_path)
    mail.agent("ceo")
    states = StateWords(mail, pauses)
    assert states.state("ceo") == "idle"
    mail.writer.store(_note("ceo", 1, wake=False))
    assert states.state("ceo") == "idle"  # mail that does not wake it is not pending
    mail.writer.store(_note("ceo", 2, wake=True))
    assert states.state("ceo") == "pending"
    pauses.set_flag("ceo", "budget")
    assert states.state("ceo") == "paused(budget)"
    mail.batches.begin("ceo")
    assert states.state("ceo") == "running"


def _note(to: str, n: int, wake: bool) -> Message:
    return Message(sender="root", to=to, type="note", title="t", body="b", wake=wake, id=f"20260101T0000{n:02d}000000-root-{n:04x}",
                   created="2026-01-01T00:00:00+00:00")
