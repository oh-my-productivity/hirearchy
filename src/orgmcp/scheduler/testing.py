"""Fakes for the scheduler: scripted roles for the unit tests of the classes that are made of them, a world over the in-memory fakes of the packages
the run lifecycle takes from (``LifecycleWorld``), whose processes are rows of a ``FakeProcessTable`` and whose time moves only when told, and the loop
over that world (``heartbeat_world``) next to an in-memory loop (``memory_world``): the two implementations of ``SchedulerLoop``."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..access.testing import StaticAccess
from ..attention import Waiting
from ..attention.testing import FixedOpenWork, FixedWaiting, ListHumanQueue
from ..attention._waiting import RootTaskWaitingOnUser
from ..attention._work import RunnableOpenWork
from ..budget.testing import FixedBudget
from ..daemon.testing import MemoryExitMarker, MemorySchedulerLock
from ..delivery.testing import RecordingDelivery
from ..eligibility import RunnableQuery
from ..eligibility.testing import MemoryFailureCounter, MemoryPauseStore, runnable_over
from ..kernel import Message, OrgPaths
from ..kernel.testing import FakeClock, ListEventSink, SequenceIdGenerator
from ..kiro import RunCommand, RunCommandBuilder
from ..mail import TaskQuery
from ..mail.testing import MemoryMailbox, memory_mailbox
from ..processes import OrphanJudge, ProcessHandle, ProcessSpawner
from ..processes._judge import PsOrphanJudge
from ..processes.testing import FakeProcessTable
from ..prompts.testing import FixedRunPrompt
from ..review import HealthReviewer, Review
from ..review.testing import ScriptedHealthReviewer
from ..runs import RunLogSink
from ..runs.testing import MemoryRuns
from ..snapshots import OrgSnapshotter
from ..snapshots.testing import MemoryIgnoreList
from ..stalls import StallLadder
from ..stalls.testing import MemoryNudges
from ..strays.testing import MemoryStrays
from ..telemetry.testing import MemoryEventRetention, MemoryProcessLabel
from ..templates.testing import RecordingNotices
from ._assembly import Lifecycle, LifecyclePorts, LoopPorts, assemble, assemble_loop
from ._loop import HeartbeatLoop
from ._ports import (
    Claim, Console, ExitPolicy, InterruptedRuns, OrphanSettler, Pacing, PhaseGuard, RunAdmission, RunEvents, RunFailures, RunInitiation,
    RunNotes, RunPreparation, RunReaper, RunRecords, RunSettling, RunSpawning, RunStarter, RunTerminating, RunWatching, SchedulerSession,
    SessionEvents, StartAnnouncing, StartFailures, StrayWatch, TickPhase, WaitGrace, WorkLeft,
)
from ._run import Exit, LoopMemory, LoopState, PreparedRun, RunCount, RunRecord, RunTable, Standing, StopWhen
from .api import SchedulerLoop

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
        self.default_exit: tuple[int, float] | None = None  # (code, seconds): every process it starts exits so, unless the table was told otherwise

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
        if self.default_exit is not None:
            self.table.will_exit(self.default_exit[0], after=self.default_exit[1])
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
    tasks: TaskQuery  # the task views of the mailboxes


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
        console, guard, count, ports, assemble(ports, clock, console, guard, count), hire, retire, mail_to, events_of, mail.tasks,
    )


# ------------------------------------------------------------------------------ scripted roles of the loop


class RecordingPhase(TickPhase):
    """Writes its name in the ``journal`` it shares with the others; ``fail`` makes it raise."""

    def __init__(self, name: str, journal: list[str], fail: Exception | None = None) -> None:
        self.name, self.journal, self.fail = name, journal, fail
        self.seen: list[tuple[Standing, int | None]] = []

    def run(self, standing: Standing, max_runs: int | None) -> None:
        self.journal.append(self.name)
        self.seen.append((standing, max_runs))
        if self.fail is not None:
            raise self.fail


class RecordingStarter(RunStarter):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.launched: list[tuple[set[str], int | None]] = []
        self.started: list[str] = []

    def launch(self, runs: RunTable, blocked: Collection[str], max_runs: int | None) -> int:
        self.journal.append("launch")
        self.launched.append((set(blocked), max_runs))
        return 0

    def start(self, runs: RunTable, addr: str) -> None:
        self.journal.append(f"start {addr}")
        self.started.append(addr)


class RecordingReaper(RunReaper):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.reaped = 0
        self.terminated = 0
        self.on_reap: Callable[[RunTable], None] | None = None

    def reap(self, runs: RunTable) -> None:
        self.journal.append("reap")
        self.reaped += 1
        if self.on_reap is not None:
            self.on_reap(runs)

    def terminate_all(self, runs: RunTable) -> None:
        self.journal.append("terminate")
        self.terminated += 1


class ScriptedWork(WorkLeft):
    """The answers it is told to give; ``asked`` keeps the standings it was asked about, as ``(question, runs, blocked, can_start)``."""

    def __init__(self, remains: bool = False, finished: bool = False, waiting: Waiting | None = None) -> None:
        self.remains_answer, self.finished_answer, self.waiting_answer = remains, finished, waiting
        self.asked: list[tuple[str, frozenset[str], frozenset[str], bool]] = []

    def _ask(self, question: str, standing: Standing) -> None:
        self.asked.append((question, frozenset(standing.runs), frozenset(standing.blocked), standing.can_start))

    def remains(self, standing: Standing) -> bool:
        self._ask("remains", standing)
        return self.remains_answer

    def finished(self, standing: Standing) -> bool:
        self._ask("finished", standing)
        return self.finished_answer

    def waiting(self, standing: Standing) -> Waiting | None:
        self._ask("waiting", standing)
        return self.waiting_answer


class ScriptedGrace(WaitGrace):
    def __init__(self, *reasons: str) -> None:
        self.reasons = list(reasons)
        self.asked = 0

    def check(self, standing: Standing) -> str:
        self.asked += 1
        return self.reasons.pop(0) if self.reasons else ""


class ScriptedExit(ExitPolicy):
    """Answers the reasons it is given, one per pass (``None`` once they are used up)."""

    def __init__(self, *reasons: str | None) -> None:
        self.reasons = list(reasons)
        self.asked: list[tuple[StopWhen, bool]] = []

    def after_tick(self, stop: StopWhen, active: bool, standing: Standing) -> str | None:
        self.asked.append((stop, active))
        return self.reasons.pop(0) if self.reasons else None


class RecordingPacing(Pacing):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.pauses = 0
        self.on_pause: Callable[[], None] | None = None

    def pause(self) -> None:
        self.journal.append("pause")
        self.pauses += 1
        if self.on_pause is not None:
            self.on_pause()


class RecordingSession(SchedulerSession):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.opened: list[tuple[str, int | None]] = []
        self.closed: list[tuple[str, int, int]] = []  # (reason, runs in flight, runs started)
        self.fail: Exception | None = None

    def open(self, mode: str, max_runs: int | None, runs: RunTable, blocked: set[str]) -> None:
        self.journal.append("open")
        self.opened.append((mode, max_runs))
        if self.fail is not None:
            raise self.fail

    def close(self, exit_reason: str, runs: RunTable, started: int) -> None:
        self.journal.append("close")
        self.closed.append((exit_reason, len(runs), started))


class RecordingClaim(Claim):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.fail: Exception | None = None

    def take(self) -> None:
        self.journal.append("take")
        if self.fail is not None:
            raise self.fail

    def give_up(self) -> None:
        self.journal.append("give up")


class RecordingSessionEvents(SessionEvents):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.starts: list[tuple[str, int | None]] = []
        self.exits: list[tuple[str, int]] = []

    def started(self, mode: str, max_runs: int | None) -> None:
        self.journal.append("started")
        self.starts.append((mode, max_runs))

    def exited(self, reason: str, runs_started: int) -> None:
        self.journal.append("exited")
        self.exits.append((reason, runs_started))


class RecordingRecovery(InterruptedRuns):
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal = journal if journal is not None else []

    def recover(self) -> None:
        self.journal.append("recover")


class RecordingSettler(OrphanSettler):
    """Settles nothing; ``blocks`` are the agents it blocks the first time it is asked."""

    def __init__(self, journal: list[str] | None = None, blocks: Collection[str] = ()) -> None:
        self.journal = journal if journal is not None else []
        self.blocks = set(blocks)
        self.calls = 0
        self.fail: Exception | None = None

    def settle(self, runs: RunTable, blocked: set[str]) -> None:
        self.journal.append("settle")
        self.calls += 1
        if self.fail is not None:
            raise self.fail
        blocked |= self.blocks
        self.blocks = set()


class RecordingNotes(RunNotes):
    def __init__(self) -> None:
        self.notes: list[tuple[dict[str, object], str]] = []

    def note(self, rec: Mapping[str, object], text: str) -> None:
        self.notes.append((dict(rec), text))


class ScriptedOrphanJudge(OrphanJudge):
    """The verdict for the record of a group (``verdicts[pgid]``; ``gone`` for one it knows nothing of)."""

    def __init__(self, verdicts: Mapping[object, str] | None = None) -> None:
        self.verdicts = dict(verdicts or {})
        self.asked: list[dict[str, object]] = []

    def judge(self, record: Mapping[str, object]) -> str:
        self.asked.append(dict(record))
        return self.verdicts.get(record.get("pgid"), "gone")


class FixedRunnable(RunnableQuery):
    """These agents could start (but for the ones excluded); ``asked`` keeps the exclusions it was asked with."""

    def __init__(self, *agents: str) -> None:
        self.agents = list(agents)
        self.asked: list[frozenset[str]] = []

    def runnable(self, exclude: Collection[str] = ()) -> list[str]:
        self.asked.append(frozenset(exclude))
        return [a for a in self.agents if a not in exclude]

    def startable(self, addr: str) -> bool:
        return addr in self.agents


class ScriptedLadder(StallLadder):
    """Climbs nothing; answers the lines it is told to; ``fail`` makes it raise."""

    def __init__(self, *lines: str) -> None:
        self.lines = list(lines)
        self.checks = 0
        self.fail: Exception | None = None

    def check(self) -> list[str]:
        self.checks += 1
        if self.fail is not None:
            raise self.fail
        lines, self.lines = self.lines, []
        return lines


# ------------------------------------------------------------------------------ the loop over the world, and in memory


@dataclass
class LoopWorld:
    """A loop and the means to give it work, finish the work and let the runs end; ``started`` is how many runs it started. The same for every implementation."""

    loop: SchedulerLoop
    give_work: Callable[[], None]  # an agent has a task of root's in its inbox
    finish_work: Callable[[], None]  # the agent answered: root's task is closed (a run in flight still ends by itself)
    let_runs_end: Callable[[], None]  # the runs in flight are over
    started: Callable[[], int]
    detail: object = None  # the world behind it, for the tests of the one implementation


@dataclass
class HeartbeatWorld:
    """The real ``HeartbeatLoop`` over the lifecycle world and in-memory ports: ``clock`` is the run clock and the cadence clock."""

    life: LifecycleWorld
    loop: HeartbeatLoop
    state: LoopState
    memory: LoopMemory
    ports: LoopPorts
    label: MemoryProcessLabel
    lock: MemorySchedulerLock
    marker: MemoryExitMarker
    ignore: MemoryIgnoreList
    retention: MemoryEventRetention
    queue: ListHumanQueue
    ladder: ScriptedLadder
    reviewer: ScriptedHealthReviewer
    judge: OrphanJudge
    nudges: MemoryNudges


def build_heartbeat_world(tmp: Path = Path("/memory"), config: str = "") -> HeartbeatWorld:
    w = lifecycle_world(tmp)
    if config:
        w.access.put_config(f"---\n{config}\n---\n# Organization\n")
    runnable = runnable_over(w.access.agents, w.box, w.pauses, w.budgets)
    nudges = MemoryNudges(w.access.agents)
    label, lock, marker, ignore = MemoryProcessLabel(), MemorySchedulerLock(w.table), MemoryExitMarker(), MemoryIgnoreList()
    retention, queue, ladder = MemoryEventRetention(w.clock), ListHumanQueue(), ScriptedLadder()
    reviewer = ScriptedHealthReviewer(Review(at=w.clock.now(), runs=0, flagged=0))
    judge = PsOrphanJudge(w.table)
    ports = LoopPorts(
        w.ports, label, lock, marker, ignore, judge, w.table, retention, queue, runnable, RunnableOpenWork(w.tasks, runnable),
        RootTaskWaitingOnUser(w.tasks, w.access.agents, w.box, w.pauses, w.budgets, runnable, nudges), ladder, reviewer, lambda: "test",
    )
    state, memory = LoopState(count=w.count), LoopMemory()
    loop = assemble_loop(ports, w.clock, w.clock, w.console, state, memory)
    return HeartbeatWorld(w, loop, state, memory, ports, label, lock, marker, ignore, retention, queue, ladder, reviewer, judge, nudges)


def heartbeat_world(tmp: Path) -> LoopWorld:
    """The real loop: a unit of work is a task of root's for a new agent (``ceo``, ``ops``, ...), whose run is a row of a process table that ends five
    seconds after it started."""
    h = build_heartbeat_world(tmp)
    w = h.life
    w.spawner.default_exit = (0, 5.0)
    names, tasks = iter(["ceo", "ops", "dev", "qa", "ux"]), list[Message]()

    def give_work() -> None:
        addr = next(names)
        w.hire(addr, 3)
        tasks.append(w.mail_to(addr, trace=f"t-{addr}"))

    def finish_work() -> None:
        for i, task in enumerate(tasks):
            w.box.store(Message(sender=task.to, to="root", type="result", title="re: t", body="ok", reply_to=task.id, status="done",
                                id=f"20260101T0001{i:02d}000000-{task.to}-aaaa", created="2026-01-01T00:00:00+00:00"))

    def let_runs_end() -> None:
        w.clock.advance(6)

    return LoopWorld(h.loop, give_work, finish_work, let_runs_end, lambda: w.count.total, h)


class MemoryLoop(SchedulerLoop):
    """A scheduler with one kind of work: ``queued`` agents that could start, ``running`` runs, and ``open_task`` (root waits for a result).

    A pass ends the runs in flight (they run for one pass) and starts the queued ones (up to the cap on runs started)."""

    def __init__(self) -> None:
        self.queued = 0
        self.running = 0
        self.open_task = False
        self.started = 0
        self.passes = 0
        self.entered = 0  # acquired and not yet released

    def _can_start(self, max_runs: int | None) -> bool:
        return max_runs is None or self.started < max_runs

    def tick(self, max_runs: int | None = None) -> bool:
        self.passes += 1
        self.running = 0
        while self.queued and self._can_start(max_runs):
            self.queued -= 1
            self.running += 1
            self.started += 1
        return bool(self.running) or (bool(self.queued) and self._can_start(max_runs))

    def finished(self, max_runs: int | None = None) -> bool:
        return not self.open_task and not self.running and not (self.queued and self._can_start(max_runs))

    def serve(self, until_idle: bool = False, max_runs: int | None = None, until_done: bool = False) -> None:
        self.entered += 1
        try:
            while True:
                active = self.tick(max_runs)
                if (until_idle and not active) or (until_done and self.finished(max_runs)):
                    break
        finally:
            self.entered -= 1

    def run_once(self, max_runs: int | None = None) -> None:
        self.entered += 1
        try:
            self.tick(max_runs)
            self.running = 0
        finally:
            self.entered -= 1


def memory_world(tmp: Path) -> LoopWorld:
    loop = MemoryLoop()

    def give_work() -> None:
        loop.queued += 1
        loop.open_task = True

    def finish_work() -> None:
        loop.open_task = False

    def let_runs_end() -> None:
        loop.running = 0

    return LoopWorld(loop, give_work, finish_work, let_runs_end, lambda: loop.started, loop)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], LoopWorld]]] = {
    SchedulerLoop: [heartbeat_world, memory_world],
}
