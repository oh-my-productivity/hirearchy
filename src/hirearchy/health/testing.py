"""The health ports over an organization on disk and over memory, and the registry the contract suites iterate over.

``HealthWorld`` is what a test gets of the analyzer: the analyzer itself and the means to prepare an organization (agents, messages, run
logs, pause flags, budgets, ORG.md) behind the ports it reads. Over disk it reads the real mailboxes, run logs and flag files; over memory it
reads ``MemoryMailbox``, ``MemoryRuns`` and ``MemoryPauseStore`` with a ``FakeClock`` that only moves when told. The same suites run over
both (``tests/test_contract_*.py``), so a consumer's unit test may use the memory world.

``FixedHealthAnalyzer`` is the stand-in for the analyzer itself: a consumer (``review``, ``dashdata``, ...) that wants to test what it does
with a report puts the ``AgentHealth`` it needs in, and gets the same guards and the same branch totals as from the real one.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from ..agents import AgentDirectory, CharterReader
from ..agents.testing import fs_agents
from ..budget.testing import FixedBudget
from ..eligibility import AgentStates
from ..eligibility.testing import PauseHarness, fs_pauses, memory_pauses
from ..kernel import ROOT, Clock, Message, OrgError, OrgPaths, aware
from ..kernel.testing import FakeClock
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..settings.testing import SettingsHarness, fs_org_settings, memory_org_settings
from ._analyzer import FileHealthAnalyzer
from ._branches import branch_totals
from ._escapes import MailEscapeCounter
from ._hired import CharterHireDates
from ._ports import CharterStamp, FsCharterStamp
from ._rework import MailClientRework
from ._thresholds import SettingsHealthThresholds
from .api import AgentHealth, HealthAnalyzer, HealthThresholds, OrgHealth

PURE = {"HealthReport", "HealthRenderer"}  # data with two derived views / a pure function of its argument: one implementation, no fake

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # the origin of the times of a world: the offsets below are seconds after it
ORG_MD = "---\nmission: test\n---\nrules\n"  # the ORG.md every world starts with: no health: block, so the defaults


def at(seconds: float) -> datetime:
    """``seconds`` after the origin of the worlds."""
    return T0 + timedelta(seconds=seconds)


def org_md(**limits: float | str) -> str:
    """An ORG.md whose ``health:`` block holds these thresholds (``stuck_after_seconds=60``, ...)."""
    block = "".join(f"  {name}: {value}\n" for name, value in limits.items())
    return f"---\nmission: test\nhealth:\n{block}---\nrules\n"


# ------------------------------------------------------------------------------ fakes


class MemoryCharterStamps(CharterStamp):
    """When each ``AGENT.md`` was written, in a table (an agent that is not in it has no charter file)."""

    def __init__(self) -> None:
        self.times: dict[str, datetime] = {}

    def modified(self, addr: str) -> datetime:
        if addr not in self.times:
            raise FileNotFoundError(2, "No such file or directory", f"{addr}/AGENT.md")
        return self.times[addr]


class StateWords(AgentStates):
    """The state word from the boxes and the flag files: running, paused(reason), pending, idle - in that order of precedence."""

    def __init__(self, mail: MailHarness, pauses: PauseHarness) -> None:
        self._mail = mail
        self._pauses = pauses

    def state(self, addr: str) -> str:
        if self._mail.reader.has_inflight(addr):
            return "running"
        reason = self._pauses.store.paused(addr)
        if reason:
            return f"paused({reason})"
        return "pending" if self._mail.reader.unread(addr) else "idle"


class FixedHealthAnalyzer(HealthAnalyzer):
    """The health of each agent is the ``AgentHealth`` a test put in (``limits`` are ignored); everything else is the real analyzer's:
    ``root`` and unknown agents are refused, a branch is the roll-up of its members, ``now`` is the one given or the clock's."""

    def __init__(self, agents: AgentDirectory, clock: Clock) -> None:
        self._agents = agents
        self._clock = clock
        self._health: dict[str, AgentHealth] = {}

    def put(self, health: AgentHealth) -> None:
        """What the analyzer will say about this agent."""
        self._health[health.addr] = health

    def agent_health(self, addr: str, now: datetime | None = None, limits: Mapping[str, float] | None = None) -> AgentHealth:
        a = self._agents.require(addr)
        if a == ROOT:
            raise OrgError("root is the human; only agents have health data")
        if a not in self._health:
            raise OrgError(f"no health was put in for {a}")
        return self._health[a]

    def org_health(self, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
        top = self._agents.require(root)
        addrs = self._agents.agents() if top == ROOT else self._agents.subtree(top)
        agents = [self.agent_health(a) for a in addrs]
        return OrgHealth(top, aware(now) or self._clock.now(), agents, branch_totals(top, addrs, {h.addr: h for h in agents}))


# ------------------------------------------------------------------------------ the worlds


class Send(Protocol):
    def __call__(
        self, sender: str, to: str, type: str, when: float, *, title: str = "t", status: str | None = None, reply_to: str | None = None,
        budget: int = 0, revises: str | None = None, service: str | None = None, wake: bool = True, feedback: str | None = None,
        source: str | None = None,
    ) -> Message: ...


@dataclass(frozen=True)
class ThresholdsHarness:
    thresholds: HealthThresholds
    configure: Callable[[str], None]  # ORG.md becomes this text


@dataclass(frozen=True)
class HealthWorld:
    """The analyzer over one organization, and the means to prepare it. Times are seconds after ``T0``; addresses: ``ceo``, ``ceo/eng``, ..."""

    analyzer: HealthAnalyzer
    clock: FakeClock  # the clock of the analyzer: it moves only when told (plus a microsecond per reading)
    agent: Callable[[str, float], None]  # (addr, hired): the agent exists, hired at that time (the charter says so)
    send: Send  # (sender, to, type, at, ...): the message is stored, as the mailbox stores it (a copy for the sender and one for the recipient)
    read: Callable[[str], None]  # the inbox of the agent is read: nothing unread is left
    start_run: Callable[[str], None]  # the inbox becomes the batch of a run in flight
    run: Callable[[str, float, float, str], Path]  # (addr, start, end, closing text): a run log named after its start, last written at its end
    pause: Callable[[str, str], None]  # (addr, text): the flag file of the agent says this
    set_budget: Callable[[str, int], None]  # the agent has this many runs left
    configure: Callable[[str], None]  # ORG.md becomes this text (``org_md(...)`` for thresholds)


def charter_text(hired: float) -> str:
    return f'---\nrole: Worker\ncreated: "{at(hired).isoformat()}"\n---\n# Role: Worker\n\nDo the work.\n'


def run_name(start: float) -> str:
    return f"{at(start):%Y%m%dT%H%M%S%f}.log"


def _thresholds(settings: SettingsHarness) -> ThresholdsHarness:
    settings.put(ORG_MD)
    return ThresholdsHarness(SettingsHealthThresholds(settings.settings), settings.put)


def fs_thresholds(tmp_path: Path) -> ThresholdsHarness:
    return _thresholds(fs_org_settings(tmp_path))


def memory_thresholds(tmp_path: Path) -> ThresholdsHarness:
    return _thresholds(memory_org_settings(tmp_path))


def _world(
    mail: MailHarness, runs: RunsHarness, pauses: PauseHarness, settings: SettingsHarness, agents: AgentDirectory, charters: CharterReader,
    stamps: CharterStamp,
) -> HealthWorld:
    settings.put(ORG_MD)
    runs.clock.t = runs.clock.origin = T0
    budgets = FixedBudget(mail.tasks, agents, charters)
    analyzer = FileHealthAnalyzer(
        agents, mail.reader, runs.reader, runs.reader, budgets, pauses.store, StateWords(mail, pauses),
        SettingsHealthThresholds(settings.settings), MailClientRework(agents, mail.reader),
        MailEscapeCounter(agents, mail.reader, runs.reader, MailClientRework(agents, mail.reader)), CharterHireDates(charters, stamps), runs.clock,
    )
    numbers = itertools.count(1)

    def agent(addr: str, hired: float) -> None:
        mail.put(f"{addr}/AGENT.md", charter_text(hired))
        runs.add_agent(addr)
        pauses.agent(addr)

    def send(
        sender: str, to: str, type: str, when: float, *, title: str = "t", status: str | None = None, reply_to: str | None = None,
        budget: int = 0, revises: str | None = None, service: str | None = None, wake: bool = True, feedback: str | None = None,
        source: str | None = None,
    ) -> Message:
        moment = at(when)
        msg = Message(
            sender=sender, to=to, type=type, title=title, body="b", status=status, reply_to=reply_to, budget=budget, revises=revises,
            service=service, wake=wake, feedback=feedback, source=source, id=f"{moment:%Y%m%dT%H%M%S%f}-{sender.replace('/', '.')}-{next(numbers):04x}", created=moment.isoformat(),
        )
        mail.writer.store(msg)
        return msg

    def read(addr: str) -> None:
        mail.batches.begin(addr)
        mail.batches.end(addr, True)

    def start_run(addr: str) -> None:
        mail.batches.begin(addr)

    def run(addr: str, start: float, end: float, closing: str) -> Path:
        path = runs.put_log(addr, run_name(start), closing)
        runs.set_mtime(path, at(end).timestamp())
        return path

    def set_budget(addr: str, runs_left: int) -> None:
        budgets.held[addr] = runs_left

    return HealthWorld(
        analyzer, runs.clock, agent, send, read, start_run, run, pauses.set_flag, set_budget, settings.put,
    )


def fs_world(tmp_path: Path) -> HealthWorld:
    disk = fs_agents(tmp_path)
    return _world(
        fs_mailbox(tmp_path), fs_runs(tmp_path), fs_pauses(tmp_path), fs_org_settings(tmp_path), disk.directory, disk.charters,
        FsCharterStamp(OrgPaths(tmp_path)),
    )


def memory_world(tmp_path: Path) -> HealthWorld:
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    stamps = MemoryCharterStamps()
    return _world(mail, memory_runs(tmp_path), memory_pauses(tmp_path), memory_org_settings(tmp_path), box.agents, box.agents, stamps)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    HealthThresholds: [fs_thresholds, memory_thresholds],
    HealthAnalyzer: [fs_world, memory_world],
}
