"""The scheduler's stall check goes through the stall ports of the runtime: the ladder for the stall phase of a pass and the task views, the nudge ledger for
``waiting_on_user``. The operator lines, the notes, the events and the ledger are covered by ``tests/test_scheduler`` (unchanged)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from hirearchy.app import Org, wiring
from hirearchy.kernel import Message
from hirearchy.stalls import NudgeLedger
from hirearchy.stalls._views import FingerprintTaskViews
from hirearchy.templates.testing import RecordingNotices
from testkit.daemon_world import waiting_on_user
from testkit.health_world import Scheduler


class FixedNudges(NudgeLedger):
    """A ledger that has these entries and the chain it is told."""

    def __init__(self, entries: dict[str, dict[str, float]], chain: list[str]) -> None:
        self._entries, self._chain = entries, chain
        self.asked: list[tuple[str, str]] = []

    def entries(self) -> dict[str, dict[str, float]]:
        return self._entries

    def chain(self, addr: str, task: Message) -> list[str]:
        self.asked.append((addr, task.id))
        return self._chain


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission", {"poll_seconds": 0.05})
    made.hire("root", "ceo", "Chief", "Run it.")
    return made


def test_the_scheduler_climbs_the_ladder_of_the_runtime(org: Org) -> None:
    org.delegate("root", "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    notices, lines = RecordingNotices(), list[str]()
    org.runtime = dataclasses.replace(org.runtime, notices=notices)
    sched = Scheduler(org, echo=lines.append, clock=lambda: 4_000_000_000.0)
    sched.tick()
    assert [call[0] for call in notices.calls] == ["nudge"] and len(lines) == 1 and lines[0].startswith("ceo: reminded about open task ")


def test_the_task_view_of_the_ladder_is_remembered(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=3)
    views = FingerprintTaskViews(org.runtime.task_query, org.runtime.mail_fingerprint)
    assert [t.id for t in views.open_tasks("ceo")] == [task.id]
    assert views.open_tasks("ceo") is views.open_tasks("ceo")  # remembered: the very same list


def test_waiting_on_user_reads_the_steps_taken_and_the_chain_from_the_nudge_ledger(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=3)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    assert waiting_on_user(org).settled is False  # type: ignore[union-attr]  # nobody was reminded yet: the ladder may still wake the holder
    org.runtime = wiring.open_runtime(org.root, {NudgeLedger: FixedNudges({task.id: {"step": 1, "at": 0}}, ["ceo", "root"])})
    waiting = waiting_on_user(org)
    assert waiting is not None and waiting.settled is True  # root has been told: nothing further up
    assert org.runtime.nudge_ledger.asked == [("ceo", task.id)]  # type: ignore[attr-defined]
