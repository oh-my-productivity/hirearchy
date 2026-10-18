"""``FakeProcessTable``: the scripting a consumer's test relies on (the contract suites show it behaves like the real table)."""

from __future__ import annotations

import io
import signal
import subprocess
from pathlib import Path

import pytest

from orgmcp.kernel.testing import FakeClock
from orgmcp.processes import ProcessDenied, ProcessGone, ProcessHandle
from orgmcp.processes.testing import FakeProcessTable

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-processes")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def table(clock: FakeClock) -> FakeProcessTable:
    return FakeProcessTable(clock)


def spawn(table: FakeProcessTable, tmp_path: Path, *argv: str, stdout: object | None = None) -> ProcessHandle:
    return table.spawn(list(argv) or ["sleep", "60"], cwd=tmp_path, env={"A": "1"}, stdin=None, stdout=stdout)


def test_a_spawn_is_recorded_with_what_it_was_given(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path, "kiro-cli", "chat")
    (record,) = table.spawned
    assert record.argv == ("kiro-cli", "chat") and record.cwd == tmp_path and dict(record.env) == {"A": "1"}
    assert record.pid == handle.pid and record.log is None


def test_pids_are_never_reused_by_the_table(table: FakeProcessTable, tmp_path: Path) -> None:
    pids = {spawn(table, tmp_path).pid for _ in range(20)}
    assert len(pids) == 20 and not pids & {table.own_ids()[0], table.own_ids()[1]}


def test_a_spawned_process_lives_until_it_is_told_to_exit(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path)
    assert handle.poll() is None
    table.exit(handle.pid, 4)
    assert handle.poll() == 4 and handle.returncode == 4
    assert not table.is_alive(handle.pid)  # reaped by the poll


def test_an_exited_child_is_a_zombie_until_its_handle_polls(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path)
    table.exit(handle.pid, 0)
    info = table.info(handle.pid)
    assert info is not None and info.state.startswith("Z") and table.is_alive(handle.pid)
    handle.wait()
    assert table.info(handle.pid) is None


def test_will_exit_scripts_the_next_spawn_only(table: FakeProcessTable, tmp_path: Path) -> None:
    table.will_exit(9)
    first, second = spawn(table, tmp_path), spawn(table, tmp_path)
    assert first.wait() == 9 and second.poll() is None


def test_a_scripted_exit_happens_when_the_clock_gets_there(table: FakeProcessTable, clock: FakeClock, tmp_path: Path) -> None:
    table.will_exit(0, after=30)
    handle = spawn(table, tmp_path)
    assert handle.poll() is None
    clock.advance(29)
    assert handle.poll() is None
    clock.advance(2)
    assert handle.poll() == 0


def test_waiting_for_a_scripted_exit_moves_the_clock_to_it(table: FakeProcessTable, clock: FakeClock, tmp_path: Path) -> None:
    table.will_exit(2, after=30)
    handle = spawn(table, tmp_path)
    start = clock.time()
    assert handle.wait(timeout=60) == 2
    assert 30 <= clock.time() - start < 31


def test_waiting_less_than_the_scripted_run_times_out(table: FakeProcessTable, clock: FakeClock, tmp_path: Path) -> None:
    table.will_exit(0, after=30)
    handle = spawn(table, tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):
        handle.wait(timeout=5)
    assert handle.poll() is None


def test_waiting_for_a_process_that_never_ends_cannot_be_answered(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path)
    with pytest.raises(RuntimeError):
        handle.wait()


def test_the_scripted_output_is_written_to_the_stdout_given(table: FakeProcessTable, tmp_path: Path) -> None:
    table.will_exit(0, output="done\n")
    sink = io.StringIO()
    spawn(table, tmp_path, stdout=sink)
    assert sink.getvalue() == "done\n"


def test_the_scripted_output_of_a_detached_process_is_appended_to_its_log(table: FakeProcessTable, tmp_path: Path) -> None:
    log = tmp_path / "scheduler.log"
    log.write_text("# before\n", encoding="utf-8")
    table.will_exit(0, output="line\n")
    handle = table.spawn_detached(["orgmcp", "run"], cwd=tmp_path, env={}, log=log)
    assert log.read_text(encoding="utf-8") == "# before\nline\n"
    assert table.spawned[-1].log == log and handle.wait() == 0


def test_sigterm_ends_a_process_unless_it_ignores_it(table: FakeProcessTable, tmp_path: Path) -> None:
    plain, proof = spawn(table, tmp_path), spawn(table, tmp_path)
    table.ignore_term(proof.pid)
    plain.signal_group(signal.SIGTERM)
    assert plain.wait() == -signal.SIGTERM
    proof.signal_group(signal.SIGTERM)
    assert proof.poll() is None
    proof.signal_group(signal.SIGKILL)
    assert proof.wait() == -signal.SIGKILL


def test_signalling_the_group_reaches_every_member_and_only_that_group(table: FakeProcessTable, tmp_path: Path) -> None:
    leader, other = spawn(table, tmp_path), spawn(table, tmp_path)
    member = table.add_member(leader.pid)
    assert table.is_session_leader(member) is False and table.is_alive(member)
    leader.signal_group(signal.SIGKILL)
    assert not table.is_alive(member) and leader.wait() == -signal.SIGKILL and other.poll() is None


def test_signalling_a_group_that_is_gone_or_denied_is_ignored(table: FakeProcessTable, tmp_path: Path) -> None:
    gone = spawn(table, tmp_path)
    gone.signal_group(signal.SIGKILL)
    gone.wait()
    gone.signal_group(signal.SIGKILL)
    denied = spawn(table, tmp_path)
    table.deny(denied.pid)
    denied.signal_group(signal.SIGKILL)
    assert denied.poll() is None


def test_a_process_added_by_hand_is_not_our_child_and_vanishes_when_it_exits(table: FakeProcessTable) -> None:
    table.add(6000, pgid=6000, sid=6000)
    table.exit(6000)
    assert table.info(6000) is None and not table.is_alive(6000)


def test_a_zombie_can_be_added_by_hand(table: FakeProcessTable) -> None:
    table.add(6000, state="Z")
    info = table.info(6000)
    assert info is not None and info.state == "Z" and table.is_alive(6000)


def test_kill_group_reports_a_leader_that_survives(table: FakeProcessTable, clock: FakeClock) -> None:
    table.add(6000, pgid=6000, sid=6000, survives_kill=True)
    start = clock.time()
    assert table.kill_group(6000, wait=0.3) is False
    assert clock.time() - start >= 0.3 and table.is_alive(6000)


def test_kill_group_of_a_denied_group_is_false_and_terminate_is_denied(table: FakeProcessTable) -> None:
    table.add(6000, pgid=6000, sid=6000, denied=True)
    assert table.kill_group(6000) is False and table.is_alive(6000)
    with pytest.raises(ProcessDenied):
        table.terminate(6000)


def test_terminate_of_a_missing_process_raises_process_gone(table: FakeProcessTable) -> None:
    with pytest.raises(ProcessGone):
        table.terminate(6001)


def test_the_table_refuses_the_pids_the_real_signaller_refuses(table: FakeProcessTable) -> None:
    pid, pgid = table.own_ids()
    for target in (0, 1, -1, pid, pgid):
        assert table.kill_group(target) is False
        with pytest.raises(ProcessDenied):
            table.terminate(target)
    assert table.signals == []


def test_the_start_time_comes_from_the_clock_in_the_format_of_ps(table: FakeProcessTable, clock: FakeClock, tmp_path: Path) -> None:
    first = spawn(table, tmp_path)
    clock.advance(3600)
    second = spawn(table, tmp_path)
    started = [table.start_time(first.pid), table.start_time(second.pid)]
    assert started[0] != started[1]
    assert started[0] == "Sun Oct 18 10:00:00 2026"  # ps -o lstart with LC_ALL=C TZ=UTC, blanks collapsed


def test_without_ps_the_table_cannot_be_read_but_the_signals_still_work(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path)
    table.ps_works = False
    assert table.start_time(handle.pid) is None and table.command_line(handle.pid) is None
    assert table.is_alive(handle.pid)
    handle.signal_group(signal.SIGKILL)
    assert handle.wait() == -signal.SIGKILL


def test_the_command_line_is_the_argv_joined(table: FakeProcessTable, tmp_path: Path) -> None:
    handle = spawn(table, tmp_path, "/venv/bin/orgmcp", "--root", "/org", "run")
    assert table.command_line(handle.pid) == "/venv/bin/orgmcp --root /org run"
