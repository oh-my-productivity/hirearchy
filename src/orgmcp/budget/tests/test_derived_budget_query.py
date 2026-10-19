"""``DerivedBudgetQuery``: what it reads, and from which port (it needs the number of runs, not the whole run-log reader)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.budget import BudgetQuery
from orgmcp.budget._ports import RunCounter
from orgmcp.budget._query import DerivedBudgetQuery
from orgmcp.kernel import Message
from orgmcp.mail.testing import MailHarness, MemoryMailbox, memory_mailbox
from orgmcp.runs.testing import MemoryRuns

CAN_HIRE = "---\nrole: R\ncan_hire: true\n---\nx\n"


class CountedRuns(RunCounter):
    """Run counts that a test sets; remembers whom it was asked about."""

    def __init__(self, used: dict[str, int] | None = None) -> None:
        self.used = used or {}
        self.asked: list[str] = []

    def count(self, addr: str) -> int:
        self.asked.append(addr)
        return self.used.get(addr, 0)


def organization(tmp_path: Path) -> tuple[MailHarness, MemoryMailbox]:
    harness = memory_mailbox(tmp_path)
    assert isinstance(harness.reader, MemoryMailbox)
    for addr in ("ceo", "ceo/eng"):
        harness.put(f"{addr}/AGENT.md", CAN_HIRE)
    return harness, harness.reader


def query(harness: MailHarness, box: MemoryMailbox, runs: RunCounter) -> BudgetQuery:
    return DerivedBudgetQuery(harness.reader, runs, box.agents, box.agents, harness.tasks)


def note(n: int, sender: str, to: str, runs: int) -> Message:
    return Message(
        sender=sender, to=to, type="note", body="b", budget=runs, id=f"20260101T0000000000{n:02d}-{sender}-aaaa", created="2026-01-01T00:00:00+00:00",
    )


def test_it_is_received_minus_given_minus_runs(tmp_path: Path) -> None:
    harness, box = organization(tmp_path)
    for msg in (note(1, "root", "ceo", 5), note(2, "root", "ceo", 2), note(3, "ceo", "ceo/eng", 3)):
        harness.writer.store(msg)
    assert query(harness, box, CountedRuns({"ceo": 1})).budget("ceo") == 7 - 3 - 1


def test_the_runs_are_asked_of_the_run_counter_for_the_normalized_address(tmp_path: Path) -> None:
    harness, box = organization(tmp_path)
    runs = CountedRuns({"ceo/eng": 4})
    assert query(harness, box, runs).budget(" /ceo/eng/ ") == -4
    assert runs.asked == ["ceo/eng"]


def test_root_is_unlimited_and_nobody_counts_its_runs(tmp_path: Path) -> None:
    harness, box = organization(tmp_path)
    runs = CountedRuns({"root": 9})
    assert query(harness, box, runs).budget("root") is None and runs.asked == []


def test_a_run_log_reader_is_a_run_counter(tmp_path: Path) -> None:
    harness, box = organization(tmp_path)
    logs = MemoryRuns(root=tmp_path)
    logs.add_agent("ceo")
    logs.create("ceo")
    assert isinstance(logs, RunCounter) and query(harness, box, logs).budget("ceo") == -1


def test_the_hint_is_for_an_agent_whose_charter_says_it_can_hire(tmp_path: Path) -> None:
    harness, box = organization(tmp_path)
    harness.put("ceo/qa/AGENT.md", "---\nrole: R\n---\nx\n")
    asked = query(harness, box, CountedRuns())
    assert asked.grant_hint("ceo/qa") == "" and asked.grant_hint("ceo").startswith("`ceo` now has 0 run(s)")
