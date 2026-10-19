"""The ``stalls`` ports over files on disk and over memory, and the registry the contract suites iterate over.

``MemoryNudges`` is the fake a consumer's test (``attention``) uses instead of ``.runtime/nudges.json``. ``StallsWorld`` is an organization with
agents, tasks, mail, pause flags, run logs and settings, a clock a test moves and the ladder over it: built over the files of a temporary directory
(``fs_world``) and over memory (``memory_world``), so that the ladder is tested against both. ``NudgesHarness`` is what a test gets for the ledger
(the two ports, and the means to look at and damage what is stored behind them).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory
from ..agents.testing import fs_agents
from ..delivery.testing import DeliveryHarness, fs_pipeline, memory_pipeline
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses
from ..kernel import RUNTIME, LedgerStore, Message, OrgPaths
from ..kernel.testing import FakeClock, ListEventSink, MemoryLedgerStore, fs_ledger_store
from ..mail import TaskQuery
from ..mail.testing import MemoryMailbox
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..settings.testing import SettingsHarness, fs_org_settings, memory_org_settings
from ..templates.testing import static_notices
from ._ladder import EscalationStallLadder
from ._nudges import LedgerNudgeLedger, chain_of, normalized
from ._ports import FsCreationTimes, FsLedgerShape, LedgerShape, NudgeRecorder
from ._views import FingerprintTaskViews
from .api import NudgeLedger, StallLadder

ORG_MD = "---\nmission: m\nstall_after: 600\n---\nrules\n"
STALL_AFTER = 600.0


class MemoryLedgerShape(LedgerShape):
    """The shape of a ledger kept as text in a table (the ``texts`` of a ``MemoryLedgerStore``)."""

    def __init__(self, texts: Mapping[str, str]) -> None:
        self._texts = texts

    def damaged(self, name: str) -> bool:
        try:
            return not isinstance(json.loads(self._texts[name]), dict)
        except (KeyError, ValueError):
            return False


class MemoryNudges(NudgeLedger, NudgeRecorder):
    """The ledger kept as the text the file would hold (``text``; ``None``: no file)."""

    def __init__(self, agents: AgentDirectory) -> None:
        self._agents = agents
        self.text: str | None = None

    def _load(self) -> tuple[object, bool]:
        """``(what the text holds, it is JSON but not an object)``; a text that cannot be parsed reads as an empty ledger."""
        if self.text is None:
            return {}, False
        try:
            data = json.loads(self.text)
        except ValueError:
            return {}, False
        return data, not isinstance(data, dict)

    def entries(self) -> dict[str, dict[str, float]]:
        return normalized(self._load()[0])

    def chain(self, addr: str, task: Message) -> list[str]:
        return chain_of(self._agents, addr, task)

    def save(self, entries: Mapping[str, Mapping[str, float]]) -> None:
        raise NotImplementedError("red: C-stalls")


class CountingTasks(TaskQuery):
    """A ``TaskQuery`` that counts the views computed (``computed``: ``(view, addr)`` in order)."""

    def __init__(self, inner: TaskQuery) -> None:
        self._inner = inner
        self.computed: list[tuple[str, str]] = []

    def open_tasks(self, addr: str) -> list[Message]:
        self.computed.append(("open_tasks", addr))
        return self._inner.open_tasks(addr)

    def outstanding(self, addr: str) -> list[Message]:
        self.computed.append(("outstanding", addr))
        return self._inner.outstanding(addr)

    def blocked_tasks(self, addr: str) -> list[Message]:
        self.computed.append(("blocked_tasks", addr))
        return self._inner.blocked_tasks(addr)


# ------------------------------------------------------------------------------ harnesses


@dataclass(frozen=True)
class NudgesHarness:
    """The two ports of the ledger, and the means to look at and damage the ledger behind their back."""

    ledger: NudgeLedger
    recorder: NudgeRecorder
    put_agent: Callable[[str], None]  # ``addr`` becomes an agent (so that it exists for ``chain``)
    text: Callable[[], str | None]  # the text of ``.runtime/nudges.json``, None when there is none
    put_text: Callable[[str], None]  # arbitrary text in the ledger


@dataclass(frozen=True)
class StallsWorld:
    """The ladder over one organization, and the means to set the organization up, move its time and look at what the ladder did."""

    ladder: StallLadder
    nudges: NudgeLedger
    clock: FakeClock  # the ladder's, the delivery's and the task stamps'; ``advance`` moves them all
    events: ListEventSink  # what the ladder emitted
    tasks: CountingTasks  # the task views the ladder computed (it asks a memo first)
    hire: Callable[[str], None]  # ``addr`` becomes an agent (its charter, its directory, its mailboxes)
    delegate: Callable[[str, str, str], Message]  # (sender, to, title): a task, delivered
    report: Callable[[Message], None]  # the assignee answers the task with a result: it is no longer open
    read: Callable[[str], None]  # the agent's inbox is processed by a run that ended (inbox -> inflight -> read)
    start_run: Callable[[str], None]  # the agent's inbox becomes the batch of a run in flight
    pause: Callable[[str, str], None]  # (addr, reason): the agent is paused
    log_run: Callable[[str, float], None]  # (addr, epoch): a run log of the agent last written then
    configure: Callable[[str], None]  # ORG.md becomes this text
    notes: Callable[[str], list[Message]]  # the notes of the runtime the agent has received, in order
    ledger_text: Callable[[], str | None]  # the text of ``.runtime/nudges.json``, None when there is none
    put_ledger_text: Callable[[str], None]  # arbitrary text in the ledger


def nudges_on_disk(tmp_path: Path) -> NudgesHarness:
    """The real ledger over ``.runtime/nudges.json`` and the agents of an organization directory."""
    ledgers, disk = fs_ledger_store(tmp_path), fs_agents(tmp_path)
    ledger = LedgerNudgeLedger(ledgers.store, FsLedgerShape(OrgPaths(tmp_path)), disk.directory)
    file = OrgPaths(tmp_path).ledger_file("nudges")
    return NudgesHarness(
        ledger, ledger, lambda addr: disk.put(f"{addr}/AGENT.md", "---\nrole: R\n---\n# R\n"),
        lambda: file.read_text(encoding="utf-8") if file.is_file() else None, lambda raw: ledgers.put_raw("nudges", raw),
    )


def nudges_in_a_ledger(tmp_path: Path) -> NudgesHarness:
    """The real ledger over a ledger store kept in memory (agents on disk)."""
    ledgers, disk = MemoryLedgerStore(), fs_agents(tmp_path)
    ledger = LedgerNudgeLedger(ledgers, MemoryLedgerShape(ledgers.texts), disk.directory)
    return NudgesHarness(
        ledger, ledger, lambda addr: disk.put(f"{addr}/AGENT.md", "---\nrole: R\n---\n# R\n"),
        lambda: ledgers.texts.get("nudges"), lambda raw: ledgers.texts.__setitem__("nudges", raw),
    )


def memory_nudges(tmp_path: Path) -> NudgesHarness:
    """The in-memory fake."""
    box = MemoryMailbox()
    fake = MemoryNudges(box.agents)

    def set_text(raw: str) -> None:
        fake.text = raw

    return NudgesHarness(fake, fake, lambda addr: box.agents.put(f"{addr}/AGENT.md", "---\nrole: R\n---\n# R\n"), lambda: fake.text, set_text)


def _world(
    h: DeliveryHarness,
    directory: AgentDirectory,
    pauses: PauseHarness,
    runs: RunsHarness,
    settings: SettingsHarness,
    ledgers: LedgerStore,
    shape: LedgerShape,
    ledger_text: Callable[[], str | None],
    put_ledger_text: Callable[[str], None],
) -> StallsWorld:
    assert h.mail is not None
    mail, clock, events = h.mail, h.clock, ListEventSink()
    tasks = CountingTasks(mail.tasks)
    nudges = LedgerNudgeLedger(ledgers, shape, directory)
    ladder = EscalationStallLadder(
        clock, settings.settings, directory, FingerprintTaskViews(tasks, mail.fingerprint), mail.reader, pauses.store, runs.reader,
        FsCreationTimes(), nudges, nudges, h.delivery, static_notices(), events,
    )
    settings.put(ORG_MD)

    def hire(addr: str) -> None:
        mail.agent(addr)
        pauses.agent(addr)
        runs.add_agent(addr)

    def delegate(sender: str, to: str, title: str) -> Message:
        return h.delivery.deliver(Message(sender=sender, to=to, type="task", title=title, body="goal", budget=3))

    def report(task: Message) -> None:
        h.delivery.deliver(Message(sender=task.to, to=task.sender, type="result", title=f"re: {task.title}", body="done", reply_to=task.id, status="done"))

    def start_run(addr: str) -> None:
        mail.batches.begin(addr)

    def read(addr: str) -> None:
        mail.batches.begin(addr)
        mail.batches.end(addr, True)

    def notes(addr: str) -> list[Message]:
        return [m for m in mail.reader.received(addr) if m.sender == RUNTIME]

    return StallsWorld(
        ladder, nudges, clock, events, tasks, hire, delegate, report, read, start_run, pauses.store.pause, lambda addr, at: runs.set_mtime(runs.put_log(addr, "20260101T000000000000.log", ""), at),
        settings.put, notes, ledger_text, put_ledger_text,
    )


def fs_world(tmp_path: Path) -> StallsWorld:
    """The ladder over an organization directory."""
    ledgers, file = fs_ledger_store(tmp_path), OrgPaths(tmp_path).ledger_file("nudges")
    return _world(
        fs_pipeline(tmp_path), fs_agents(tmp_path).directory, fs_pauses(tmp_path), fs_runs(tmp_path), fs_org_settings(tmp_path), ledgers.store,
        FsLedgerShape(OrgPaths(tmp_path)), lambda: file.read_text(encoding="utf-8") if file.is_file() else None, lambda raw: ledgers.put_raw("nudges", raw),
    )


def memory_world(tmp_path: Path) -> StallsWorld:
    """The ladder over the in-memory ports."""
    h = memory_pipeline(tmp_path)
    box = h.mail.reader if h.mail is not None else None
    assert isinstance(box, MemoryMailbox)
    ledgers = MemoryLedgerStore()
    return _world(
        h, box.agents, memory_pauses(tmp_path), memory_runs(tmp_path), memory_org_settings(tmp_path), ledgers, MemoryLedgerShape(ledgers.texts),
        lambda: ledgers.texts.get("nudges"), lambda raw: ledgers.texts.__setitem__("nudges", raw),
    )


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    NudgeLedger: [nudges_on_disk, nudges_in_a_ledger, memory_nudges],
    StallLadder: [fs_world, memory_world],
}
