"""The parts of starting one run: the preparation, the process, the failure to start, the announcement, and the order they are put in."""

from __future__ import annotations

import subprocess
from pathlib import Path

from orgmcp.kernel.testing import FakeClock
from orgmcp.processes.testing import FakeProcessTable
from orgmcp.scheduler._run import RunRecord
from orgmcp.scheduler._starter import BatchPreparer, CommandSpawner, SingleRunStarter, StartAnnouncer, StartFailureHandler
from orgmcp.scheduler.testing import (
    CatchingGuard, CapturingSpawner, LifecycleWorld, MemoryRunRecords, NullSink, RecordingAnnouncing, RecordingConsole, RecordingRunEvents,
    RecordingRunFailures, RecordingStartFailures, ScriptedCommands, ScriptedPreparation, ScriptedSpawning, ScriptedStrayWatch, lifecycle_world,
)

from ._support import prepared


def preparer(w: LifecycleWorld) -> BatchPreparer:
    return BatchPreparer(w.box, w.budgets, w.runs_store, w.prompts, w.count)


def test_the_preparation_takes_the_batch_creates_the_log_counts_the_run_and_writes_the_prompt() -> None:
    w = lifecycle_world()
    w.hire("ceo", budget=3)
    first, second = w.mail_to("ceo", trace="t2", title="a"), w.mail_to("ceo", trace="t1", title="b")
    run = preparer(w).prepare("ceo")
    assert [m.id for m in run.batch] == [first.id, second.id] and w.box.messages("ceo", "inbox") == []
    assert (run.budget_before, run.traces, run.prompt) == (3, ("t1", "t2"), "THE PROMPT")
    assert run.log.parent == Path("/memory/org/ceo/runs") and run.run_id == f"ceo@{run.log.stem}" and w.runs_store.count("ceo") == 1
    assert w.count.total == 1 and run.sink.path == run.log and w.prompts.asked[0][0] == "ceo"


def test_the_run_is_counted_before_the_prompt_is_written_and_a_prompt_that_fails_leaves_the_log() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")

    def refuse(addr: str, batch: object) -> str:
        raise RuntimeError("no such agent")

    w.prompts.run_prompt = refuse  # type: ignore[method-assign]
    try:
        preparer(w).prepare("ceo")
    except RuntimeError:
        pass
    assert w.count.total == 1 and w.runs_store.count("ceo") == 1


def test_the_process_gets_the_prompt_on_stdin_and_the_log_the_header_the_command_and_the_prompt() -> None:
    clock = FakeClock()
    spawner, commands = CapturingSpawner(FakeProcessTable(clock)), ScriptedCommands(("kiro-cli", "chat"), Path("/ws"), {"PATH": "/bin"})
    p = prepared("ceo")
    handle = CommandSpawner(commands, spawner).spawn(p)
    (spawned,) = spawner.spawned
    assert spawned.argv == ("kiro-cli", "chat") and spawned.cwd == Path("/ws") and spawned.stdin == "THE PROMPT" and spawned.stdout is p.sink
    assert dict(spawned.env) == {"PATH": "/bin", "ORG_RUN_ID": p.run_id}
    assert isinstance(p.sink, NullSink) and p.sink.text == (
        "# run of ceo, 1 message(s)\n# senders: root\n# cwd: /ws\n# cmd: kiro-cli chat <prompt on stdin>\n"
        "# ---- prompt ----\nTHE PROMPT\n# ---- output ----\n")
    assert handle.pid == spawner.table.spawned[0].pid


def test_a_command_that_cannot_be_built_starts_nothing() -> None:
    spawner, commands = CapturingSpawner(FakeProcessTable()), ScriptedCommands()
    commands.fail = FileNotFoundError("kiro-cli")
    try:
        CommandSpawner(commands, spawner).spawn(prepared())
    except FileNotFoundError:
        pass
    assert spawner.spawned == []


def test_a_start_that_failed_is_logged_given_back_and_counted_as_a_failed_run() -> None:
    w = lifecycle_world()
    w.hire("ceo")
    w.mail_to("ceo")
    run = preparer(w).prepare("ceo")
    events, failures = RecordingRunEvents(), RecordingRunFailures()
    StartFailureHandler(w.box, events, failures).handle(run, FileNotFoundError("kiro-cli"))
    assert w.box.messages("ceo", "inbox") != [] and w.box.messages("ceo", "inflight") == []
    assert events.calls == [("not_started", "ceo", "kiro-cli")] and failures.failed_runs == [("ceo", run.log, run.traces)]
    assert w.runs_store.read_log(run.log) == b"\n# failed to start: kiro-cli\n"


def test_the_announcement_emits_records_and_says_so_and_a_registry_that_fails_is_only_guarded() -> None:
    events, records, guard, console = RecordingRunEvents(), MemoryRunRecords(), CatchingGuard(), RecordingConsole()
    table = FakeProcessTable()
    p = prepared("ceo")
    run = RunRecord("ceo", table.spawn(["x"], cwd=Path("/"), env={}, stdin=None, stdout=None), p.log, p.sink, 0.0, 1, run_id=p.run_id)
    announcing = StartAnnouncer(events, records, guard, console)
    announcing.announce(run, p)
    assert events.calls == [("started", "ceo", run.proc.pid)] and records.records == {"ceo": run} and console.lines == ["ceo: started run (1 message(s))"]
    records.fail = OSError("disk full")
    announcing.announce(run, p)
    assert guard.errors == [("run record", "OSError: disk full")] and console.lines[-1] == "ceo: started run (1 message(s))"


def test_a_started_run_joins_the_table_with_the_strays_before_it() -> None:
    clock, table = FakeClock(), FakeProcessTable()
    p, handle = prepared("ceo"), table.spawn(["x"], cwd=Path("/"), env={}, stdin=None, stdout=None)
    announcing, failures, strays = RecordingAnnouncing(), RecordingStartFailures(), ScriptedStrayWatch({"/ws/ceo": 1.0})
    starter = SingleRunStarter(ScriptedPreparation(p), ScriptedSpawning(handle), strays, CatchingGuard(), failures, announcing, clock)
    runs: dict[str, RunRecord] = {}
    starter.start(runs, "ceo")
    run = runs["ceo"]
    assert (run.proc, run.log, run.logf, run.started, run.batch, run.strays, run.run_id, run.traces, run.budget_before) == (
        handle, p.log, p.sink, clock.time(), 1, {"/ws/ceo": 1.0}, p.run_id, p.traces, 3)
    assert announcing.announced == [(run, p)] and failures.handled == [] and strays.asked_before == ["ceo"]


def test_a_failing_stray_probe_is_guarded_and_the_run_starts_without_strays() -> None:
    clock, table = FakeClock(), FakeProcessTable()
    strays, guard = ScriptedStrayWatch(), CatchingGuard()
    strays.fail_before = OSError("boom")
    starter = SingleRunStarter(ScriptedPreparation(prepared()), ScriptedSpawning(table.spawn(["x"], cwd=Path("/"), env={}, stdin=None, stdout=None)),
                               strays, guard, RecordingStartFailures(), RecordingAnnouncing(), clock)
    runs: dict[str, RunRecord] = {}
    starter.start(runs, "ceo")
    assert runs["ceo"].strays is None and guard.errors == [("stray check", "OSError: boom")]


def test_a_process_that_does_not_start_is_handled_and_not_in_the_table() -> None:
    spawning, failures, announcing = ScriptedSpawning(), RecordingStartFailures(), RecordingAnnouncing()
    spawning.fail = subprocess.SubprocessError("no exec")
    starter = SingleRunStarter(ScriptedPreparation(prepared()), spawning, ScriptedStrayWatch(), CatchingGuard(), failures, announcing, FakeClock())
    runs: dict[str, RunRecord] = {}
    starter.start(runs, "ceo")
    assert runs == {} and announcing.announced == [] and [e for _, e in failures.handled] == ["no exec"]
