"""The eligibility ports over files on disk and over memory, and the registry the contract suites iterate over.

``MemoryPauseStore`` and ``MemoryFailureCounter`` are the fakes a consumer's test uses instead of flag files and a ledger. They pass the same
contract suites as the real classes (``tests/test_contract_*.py``). ``PauseHarness`` and ``FailureHarness`` are what a test gets for those two ports
(the port, and the means to look at and damage what is stored behind it); ``EligibilityWorld`` is an organization with mail, budgets and pause
flags for ``AgentStates`` and ``RunnableQuery``, whose budgets are the numbers a test sets (``orgmcp.budget.testing.FixedBudget``).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory, CharterReader
from ..agents.testing import fs_agents
from ..budget.testing import FixedBudget
from ..kernel import RUNTIME, EventSink, Message, OrgPaths
from ..kernel.testing import ListEventSink, MemoryLedgerStore, fs_ledger_store
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ._caching import CachingPauseStore
from ._failures import LedgerFailureCounter
from ._pause import FsPauseStore
from ._ports import FsDirectoryProbe, FsLedgerShape, LedgerShape
from ._runnable import DerivedRunnableQuery
from ._states import DerivedAgentStates
from .api import AgentStates, FailureCounter, PauseStore, RunnableQuery


class MemoryPauseStore(PauseStore):
    """The flag files in a table: ``flags`` holds the text of each, as the file would."""

    def __init__(self, events: EventSink) -> None:
        self.flags: dict[str, str] = {}
        raise NotImplementedError("red: B-eligibility")

    def paused(self, addr: str) -> str | None:
        raise NotImplementedError("red: B-eligibility")

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        raise NotImplementedError("red: B-eligibility")


class MemoryFailureCounter(FailureCounter):
    """The ledger kept as the text the file would hold (``text``; ``None``: no file)."""

    def __init__(self) -> None:
        self.text: str | None = None
        raise NotImplementedError("red: B-eligibility")

    def record(self, addr: str) -> int:
        raise NotImplementedError("red: B-eligibility")

    def clear(self, addr: str) -> None:
        raise NotImplementedError("red: B-eligibility")

    def repair(self) -> bool:
        raise NotImplementedError("red: B-eligibility")


class MemoryLedgerShape(LedgerShape):
    """The shape of a ledger kept as text in a table (the ``texts`` of a ``MemoryLedgerStore``)."""

    def __init__(self, texts: Mapping[str, str]) -> None:
        self._texts = texts

    def damaged(self, name: str) -> bool:
        raise NotImplementedError("red: B-eligibility")


# ------------------------------------------------------------------------------ harnesses


@dataclass(frozen=True)
class PauseHarness:
    """A pause store, the events it emitted, and the means to look at and change the flag files behind its back."""

    store: PauseStore
    events: ListEventSink
    agent: Callable[[str], None]  # the agent exists (its directory, where the flag file lives)
    flag: Callable[[str], str | None]  # the text of the flag file of an agent, None when there is none
    set_flag: Callable[[str, str], None]  # a flag file with this text


@dataclass(frozen=True)
class FailureHarness:
    """A failure counter and the means to look at and damage its ledger behind its back."""

    counter: FailureCounter
    text: Callable[[], str | None]  # the text of ``.runtime/failures.json``, None when there is none
    put_text: Callable[[str], None]  # arbitrary text in the ledger


@dataclass(frozen=True)
class EligibilityWorld:
    """``AgentStates`` and ``RunnableQuery`` over one organization of mailboxes, pause flags and budgets a test sets."""

    states: AgentStates
    runnable: RunnableQuery
    pauses: PauseStore
    events: ListEventSink
    agent: Callable[[str], None]  # the agent exists, with no mail, no budget and no flag
    mail_to: Callable[[str, bool], None]  # (addr, wakes): one more message in the inbox
    begin_run: Callable[[str], None]  # the inbox becomes the batch of a run in flight
    set_budget: Callable[[str, int], None]  # the agent has this many runs left
    set_flag: Callable[[str, str], None]  # a flag file with this text (for what ``pause`` would not write)


def _read(path: Path) -> str | None:
    return path.read_bytes().decode("utf-8") if path.is_file() else None


def _fs_pauses(tmp_path: Path, wrap: Callable[[PauseStore, OrgPaths], PauseStore]) -> PauseHarness:
    paths, events = OrgPaths(tmp_path), ListEventSink()

    def agent(addr: str) -> None:
        paths.agent_dir(addr).mkdir(parents=True, exist_ok=True)

    def set_flag(addr: str, text: str) -> None:
        agent(addr)
        (paths.agent_dir(addr) / ".paused").write_bytes(text.encode("utf-8"))

    def flag(addr: str) -> str | None:
        return _read(paths.agent_dir(addr) / ".paused")

    return PauseHarness(wrap(FsPauseStore(paths, events), paths), events, agent, flag, set_flag)


def fs_pauses(tmp_path: Path) -> PauseHarness:
    return _fs_pauses(tmp_path, lambda store, paths: store)


def caching_pauses(tmp_path: Path) -> PauseHarness:
    """The dashboard's decorator over the flag files on disk."""
    return _fs_pauses(tmp_path, lambda store, paths: CachingPauseStore(store, FsDirectoryProbe(paths)))


def memory_pauses(tmp_path: Path) -> PauseHarness:
    events = ListEventSink()
    store = MemoryPauseStore(events)
    return PauseHarness(store, events, lambda addr: None, store.flags.get, store.flags.__setitem__)


def fs_failures(tmp_path: Path) -> FailureHarness:
    ledgers = fs_ledger_store(tmp_path)
    file = OrgPaths(tmp_path).ledger_file("failures")
    return FailureHarness(
        LedgerFailureCounter(ledgers.store, FsLedgerShape(OrgPaths(tmp_path))), lambda: _read(file), lambda raw: ledgers.put_raw("failures", raw),
    )


def ledger_failures(tmp_path: Path) -> FailureHarness:
    """The real counter over a ledger kept in memory."""
    ledgers = MemoryLedgerStore()

    def put_text(raw: str) -> None:
        ledgers.texts["failures"] = raw

    return FailureHarness(LedgerFailureCounter(ledgers, MemoryLedgerShape(ledgers.texts)), lambda: ledgers.texts.get("failures"), put_text)


def memory_failures(tmp_path: Path) -> FailureHarness:
    counter = MemoryFailureCounter()

    def put_text(raw: str) -> None:
        counter.text = raw

    return FailureHarness(counter, lambda: counter.text, put_text)


def _world(mail: MailHarness, agents: AgentDirectory, charters: CharterReader, pauses: PauseHarness) -> EligibilityWorld:
    budgets = FixedBudget(mail.tasks, agents, charters)
    numbers = itertools.count(1)

    def mail_to(addr: str, wakes: bool) -> None:
        stamp = next(numbers)
        mail.writer.store(Message(
            sender=RUNTIME, to=addr, type="note", title="t", body="b", id=f"20260101T000000{stamp:06d}-runtime-aaaa",
            created="2026-01-01T00:00:00+00:00", wake=wakes,
        ))

    def agent(addr: str) -> None:
        mail.agent(addr)
        pauses.agent(addr)

    def begin_run(addr: str) -> None:
        mail.batches.begin(addr)

    def set_budget(addr: str, runs: int) -> None:
        budgets.held[addr] = runs

    return EligibilityWorld(
        DerivedAgentStates(mail.reader, pauses.store),
        DerivedRunnableQuery(agents, mail.reader, pauses.store, budgets),
        pauses.store,
        pauses.events,
        agent,
        mail_to,
        begin_run,
        set_budget,
        pauses.set_flag,
    )


def fs_world(tmp_path: Path) -> EligibilityWorld:
    disk = fs_agents(tmp_path)
    return _world(fs_mailbox(tmp_path), disk.directory, disk.charters, fs_pauses(tmp_path))


def memory_world(tmp_path: Path) -> EligibilityWorld:
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    return _world(mail, box.agents, box.agents, memory_pauses(tmp_path))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    PauseStore: [fs_pauses, caching_pauses, memory_pauses],
    FailureCounter: [fs_failures, ledger_failures, memory_failures],
    AgentStates: [fs_world, memory_world],
    RunnableQuery: [fs_world, memory_world],
}
