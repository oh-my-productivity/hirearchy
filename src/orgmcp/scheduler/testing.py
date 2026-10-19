"""Fakes for the run lifecycle: scripted roles for the unit tests of the classes that are made of them, and a world over the in-memory fakes of the
packages the lifecycle takes from (``LifecycleWorld``), whose processes are rows of a ``FakeProcessTable`` and whose time moves only when told."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..access.testing import StaticAccess
from ..budget.testing import FixedBudget
from ..delivery.testing import RecordingDelivery
from ..eligibility.testing import MemoryFailureCounter, MemoryPauseStore
from ..kernel import Message, OrgPaths
from ..kernel.testing import FakeClock, ListEventSink, SequenceIdGenerator
from ..kiro import RunCommand, RunCommandBuilder
from ..mail.testing import MemoryMailbox, memory_mailbox
from ..processes import ProcessHandle, ProcessSpawner
from ..processes.testing import FakeProcessTable
from ..prompts.testing import FixedRunPrompt
from ..runs import RunLogSink
from ..runs.testing import MemoryRuns
from ..snapshots import OrgSnapshotter
from ..strays.testing import MemoryStrays
from ..templates.testing import RecordingNotices
from ._assembly import Lifecycle, LifecyclePorts, assemble
from ._ports import (
    Console, PhaseGuard, RunAdmission, RunEvents, RunFailures, RunInitiation, RunPreparation, RunRecords, RunSettling, RunSpawning,
    RunTerminating, RunWatching, StartAnnouncing, StartFailures, StrayWatch,
)
from ._run import Exit, PreparedRun, RunCount, RunRecord, RunTable

PROMPT = "THE PROMPT"


class RecordingConsole(Console):
    def __init__(self) -> None:
        self.lines: list[str] = []

    def say(self, line: str) -> None:
        self.lines.append(line)


class CatchingGuard(PhaseGuard):
    """Runs the phase; a failure is kept in ``errors`` as (phase, "Type: message") and goes no further, like the guard of the loop."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.phases: list[str] = []

    def guard(self, phase: str, fn: Callable[[], None]) -> None:
        self.phases.append(phase)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a best-effort phase
            self.errors.append((phase, f"{type(exc).__name__}: {exc}"))


class RecordingSnapshotter(OrgSnapshotter):
    def __init__(self) -> None:
        self.commits: list[str] = []

    def init_repository(self) -> None:
        pass

    def commit(self, message: str) -> None:
        self.commits.append(message)


class ScriptedCommands(RunCommandBuilder):
    """The command of every run is the one it is given; ``fail`` makes building it fail (kiro-cli missing, a profile that cannot be written)."""

    def __init__(self, argv: Sequence[str] = ("kiro-cli", "chat"), cwd: Path = Path("/memory/work"), env: Mapping[str, str] | None = None) -> None:
        self.argv, self.cwd, self.env = tuple(argv), cwd, dict(env or {"PATH": "/bin", "ORG_AGENT": "x"})
        self.fail: Exception | None = None
        self.built: list[tuple[str, str]] = []

    def build(self, addr: str, prompt: str) -> RunCommand:
        self.built.append((addr, prompt))
        if self.fail is not None:
            raise self.fail
        return RunCommand(self.argv, self.cwd, self.env)


@dataclass(frozen=True)
class Spawned:
    """What a process was started with: the text of its stdin is read at the moment it starts (the file is closed afterwards)."""

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    stdin: str
    stdout: object | None


class CapturingSpawner(ProcessSpawner):
    """A ``FakeProcessTable`` that remembers the stdin it was given; ``fail`` makes starting a process fail."""

    def __init__(self, table: FakeProcessTable) -> None:
        self.table = table
        self.fail: Exception | None = None
        self.spawned: list[Spawned] = []

    def spawn(
        self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], stdin: object | None, stdout: object | None
    ) -> ProcessHandle:
        if self.fail is not None:
            raise self.fail
        text = ""
        if stdin is not None and hasattr(stdin, "read") and hasattr(stdin, "seek"):
            text = stdin.read().decode("utf-8")  # a binary temporary file, read from where the caller left it
            stdin.seek(0)
        self.spawned.append(Spawned(tuple(argv), cwd, dict(env), text, stdout))
        return self.table.spawn(argv, cwd=cwd, env=env, stdin=stdin, stdout=stdout)

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], log: Path) -> ProcessHandle:
        return self.table.spawn_detached(argv, cwd=cwd, env=env, log=log)


# ------------------------------------------------------------------------------ scripted roles (for the classes made of them)


class RecordingRunEvents(RunEvents):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | str | None]] = []  # (kind, agent, pid / code / error)

    def started(self, prepared: PreparedRun, pid: int | None) -> None:
        self.calls.append(("started", prepared.addr, pid))

    def ended(self, run: RunRecord, code: int | None, error: str | None = None) -> None:
        self.calls.append(("ended", run.addr, code if error is None else error))

    def not_started(self, prepared: PreparedRun, error: Exception) -> None:
        self.calls.append(("not_started", prepared.addr, str(error)))


class MemoryRunRecords(RunRecords):
    def __init__(self) -> None:
        self.records: dict[str, RunRecord] = {}
        self.forgotten: list[tuple[str, ...]] = []
        self.fail: Exception | None = None

    def record(self, addr: str, run: RunRecord) -> None:
        if self.fail is not None:
            raise self.fail
        self.records[addr] = run

    def forget(self, *addrs: str) -> None:
        self.forgotten.append(addrs)
        if self.fail is not None:
            raise self.fail
        for addr in addrs:
            if self.records.pop(addr, None) is not None:
                break


class RecordingRunFailures(RunFailures):
    def __init__(self) -> None:
        self.failed_runs: list[tuple[str, Path, tuple[str, ...]]] = []
        self.cleared_agents: list[str] = []

    def failed(self, addr: str, log: Path, traces: Sequence[str]) -> None:
        self.failed_runs.append((addr, log, tuple(traces)))

    def cleared(self, addr: str) -> None:
        self.cleared_agents.append(addr)


class ScriptedStrayWatch(StrayWatch):
    def __init__(self, before: dict[str, float] | None = None) -> None:
        self.answer = {} if before is None else before
        self.fail_before: Exception | None = None
        self.fail_after: Exception | None = None
        self.asked_before: list[str] = []
        self.checked: list[str] = []

    def before(self, addr: str) -> dict[str, float]:
        self.asked_before.append(addr)
        if self.fail_before is not None:
            raise self.fail_before
        return self.answer

    def after(self, run: RunRecord) -> None:
        self.checked.append(run.addr)
        if self.fail_after is not None:
            raise self.fail_after


class ScriptedAdmission(RunAdmission):
    def __init__(self, allowed: Collection[str]) -> None:
        self.allowed = set(allowed)
        self.asked: list[str] = []

    def admit(self, addr: str) -> bool:
        self.asked.append(addr)
        return addr in self.allowed


class RecordingInitiation(RunInitiation):
    """Starting a run adds a run to the table and counts it, as the real one does."""

    def __init__(self, count: RunCount, proc: Callable[[], ProcessHandle]) -> None:
        self.started: list[str] = []
        self._count, self._proc = count, proc

    def start(self, runs: RunTable, addr: str) -> None:
        self.started.append(addr)
        self._count.total += 1
        runs[addr] = RunRecord(addr, self._proc(), Path("/memory/org") / addr / "runs" / "x.log", NullSink(), 0.0, 1)


class NullSink(RunLogSink):
    def __init__(self) -> None:
        self.text = ""
        self.closed = False

    @property
    def path(self) -> Path:
        return Path("/memory/null.log")

    def write(self, text: str) -> None:
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        self.text += text

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class ScriptedPreparation(RunPreparation):
    def __init__(self, prepared: PreparedRun) -> None:
        self.prepared = prepared
        self.fail: Exception | None = None
        self.asked: list[str] = []

    def prepare(self, addr: str) -> PreparedRun:
        self.asked.append(addr)
        if self.fail is not None:
            raise self.fail
        return self.prepared


class ScriptedSpawning(RunSpawning):
    def __init__(self, handle: ProcessHandle | None = None) -> None:
        self.handle = handle
        self.fail: Exception | None = None
        self.spawned: list[PreparedRun] = []

    def spawn(self, prepared: PreparedRun) -> ProcessHandle:
        self.spawned.append(prepared)
        if self.fail is not None or self.handle is None:
            raise self.fail or RuntimeError("no process scripted")
        return self.handle


class RecordingStartFailures(StartFailures):
    def __init__(self) -> None:
        self.handled: list[tuple[PreparedRun, str]] = []

    def handle(self, prepared: PreparedRun, error: Exception) -> None:
        self.handled.append((prepared, str(error)))


class RecordingAnnouncing(StartAnnouncing):
    def __init__(self) -> None:
        self.announced: list[tuple[RunRecord, PreparedRun]] = []

    def announce(self, run: RunRecord, prepared: PreparedRun) -> None:
        self.announced.append((run, prepared))


class ScriptedWatching(RunWatching):
    """The exits it is told, per agent (an agent without one is still running)."""

    def __init__(self, exits: Mapping[str, Exit] | None = None) -> None:
        self.exits = dict(exits or {})
        self.watched: list[str] = []

    def watch(self, run: RunRecord) -> Exit | None:
        self.watched.append(run.addr)
        return self.exits.get(run.addr)


class RecordingSettling(RunSettling):
    def __init__(self) -> None:
        self.settled: list[tuple[str, Exit, float]] = []
        self.fail: Exception | None = None

    def settle(self, run: RunRecord, exit: Exit, elapsed: float) -> None:
        if self.fail is not None:
            raise self.fail
        self.settled.append((run.addr, exit, elapsed))


class RecordingTerminating(RunTerminating):
    def __init__(self) -> None:
        self.calls = 0

    def terminate_all(self, runs: RunTable) -> None:
        self.calls += 1


# ------------------------------------------------------------------------------ the world


@dataclass
class LifecycleWorld:
    """The starter and the reaper over in-memory ports. ``clock`` is the run clock; ``ports`` can be replaced and ``lifecycle`` assembled again."""

    clock: FakeClock
    table: FakeProcessTable
    spawner: CapturingSpawner
    box: MemoryMailbox
    runs_store: MemoryRuns
    pauses: MemoryPauseStore
    failure_counter: MemoryFailureCounter
    budgets: FixedBudget
    delivery: RecordingDelivery
    notices: RecordingNotices
    events: ListEventSink
    access: StaticAccess
    strays: MemoryStrays
    snapshots: RecordingSnapshotter
    prompts: FixedRunPrompt
    commands: ScriptedCommands
    console: RecordingConsole
    guard: CatchingGuard
    count: RunCount
    ports: LifecyclePorts
    lifecycle: Lifecycle
    hire: Callable[..., None]  # (addr, budget=3): the agent exists (a charter, a directory for its runs) and holds this many runs
    retire: Callable[[str], None]  # the agent's files are gone
    mail_to: Callable[..., Message]  # (addr, title="t", sender="root", trace=None, wake=True): a task in the inbox
    events_of: Callable[[str], list[dict[str, object]]]  # the events of this kind: envelope and fields in one dictionary


def lifecycle_world(tmp: Path = Path("/memory")) -> LifecycleWorld:
    clock = FakeClock()
    table = FakeProcessTable(clock)
    spawner = CapturingSpawner(table)
    mail = memory_mailbox(tmp)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    access = StaticAccess(agents=box.agents)
    runs_store = MemoryRuns(clock, access.agents.root)
    events = ListEventSink()
    pauses = MemoryPauseStore(events)
    budgets = FixedBudget(mail.tasks, access.agents, access.agents)
    delivery = RecordingDelivery(clock, SequenceIdGenerator(clock))
    notices = RecordingNotices()
    snapshots = RecordingSnapshotter()
    prompts = FixedRunPrompt(PROMPT)
    commands = ScriptedCommands()
    console = RecordingConsole()
    guard = CatchingGuard()
    count = RunCount()
    counter = MemoryFailureCounter()
    strays = MemoryStrays()
    ports = LifecyclePorts(
        access.agents, access.settings, box, box, pauses, counter, budgets, delivery, notices, access, runs_store, runs_store, prompts, strays, strays,
        snapshots, events, spawner, table, OrgPaths(access.agents.root), commands,
    )
    def hire(addr: str, budget: int = 3) -> None:
        box.agents.put(f"{addr}/AGENT.md", "---\nrole: Worker\n---\n# Role: Worker\n\nDo the work.\n")
        runs_store.add_agent(addr)
        budgets.held[addr] = budget

    def retire(addr: str) -> None:
        for path in [p for p in box.agents.files if p == addr or p.startswith(f"{addr}/")]:
            del box.agents.files[path]

    def mail_to(addr: str, title: str = "t", sender: str = "root", trace: str | None = None, wake: bool = True) -> Message:
        box.store(Message(
            sender=sender, to=addr, type="task", title=title, body="b", id=f"20260101T0000{len(box.agents.files):02d}000000-{sender}-aaaa",
            created="2026-01-01T00:00:00+00:00", wake=wake, trace=trace,
        ))
        return next(m for m in box.messages(addr, "inbox") if m.title == title)

    def events_of(kind: str) -> list[dict[str, object]]:
        return [{"actor": e.actor, "run": e.run, "trace": e.trace, "proc": e.proc, **e.fields} for e in events.events if e.kind == kind]

    return LifecycleWorld(
        clock, table, spawner, box, runs_store, pauses, counter, budgets, delivery, notices, events, access, strays, snapshots, prompts, commands,
        console, guard, count, ports, assemble(ports, clock, console, guard, count), hire, retire, mail_to, events_of,
    )
