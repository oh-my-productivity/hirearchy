"""Contract of ``SchedulerStatus``: what the pidfile and the process table say about the scheduler of an organization.

Over the files of a directory and a scripted process table, over the same files and the machine's processes (only processes the test started
are ever touched), and over the in-memory fake."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp.attention import Waiting
from orgmcp.daemon import FINISHED, SchedulerState, SchedulerStatus
from orgmcp.daemon.testing import IMPLEMENTATIONS, LIVE_TEXT, SINCE, StatusWorld

from ._support import build, worlds


@pytest.fixture(params=worlds(IMPLEMENTATIONS[SchedulerStatus]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[StatusWorld]:
    world = build(request, tmp_path, StatusWorld)
    assert isinstance(world.status, SchedulerStatus)
    yield world
    world.close()


# ------------------------------------------------------------------------------ state


def test_without_a_pidfile_the_scheduler_is_stopped(w: StatusWorld) -> None:
    w.no_pidfile()
    assert w.status.state() == SchedulerState("stopped")
    assert w.status.describe() == "scheduler: stopped"


@pytest.mark.parametrize("text", ["garbage", "", "  \n", "1", "0", "-5", "12abc"])
def test_a_pidfile_that_names_no_usable_pid_means_stopped(w: StatusWorld, text: str) -> None:
    w.pidfile(text)
    assert w.status.state() == SchedulerState("stopped")


def test_a_pidfile_of_a_process_that_is_gone_is_stale_and_means_stopped(w: StatusWorld) -> None:
    w.gone()
    assert w.status.state() == SchedulerState("stopped")
    assert w.status.describe() == "scheduler: stopped"


def test_a_live_process_with_the_command_line_of_this_organizations_scheduler_is_running(w: StatusWorld) -> None:
    pid = w.scheduler()
    assert w.status.state() == SchedulerState("running", pid, SINCE)


def test_running_is_described_with_its_pid_and_since_when(w: StatusWorld) -> None:
    pid = w.scheduler()
    assert w.status.describe() == f"scheduler: running (pid {pid}, since {SINCE})"


def test_a_live_process_that_is_not_a_scheduler_is_not_trusted(w: StatusWorld) -> None:
    pid = w.process(["vim", f"{w.root}/ORG.md"])
    command = f"{LIVE_TEXT} vim {w.root}/ORG.md"
    assert w.status.state() == SchedulerState("unverified", pid, SINCE, f"its command line is {command!r}")


def test_the_scheduler_of_another_organization_is_not_trusted(w: StatusWorld) -> None:
    pid = w.process(["orgmcp", "--root", str(w.root.parent / "other-org"), "run"])
    assert w.status.state().state == "unverified" and w.status.state().pid == pid


def test_unverified_is_described_as_unknown_and_not_trusted(w: StatusWorld) -> None:
    pid = w.process(["vim", "notes.txt"])
    assert w.status.describe() == (
        f"scheduler: unknown - .runtime/scheduler.pid names pid {pid}, which is alive but not verified to be this org's scheduler "
        f"(its command line is '{LIVE_TEXT} vim notes.txt'); not trusted"
    )


def test_when_the_process_table_cannot_be_read_a_live_pid_is_unverified(w: StatusWorld) -> None:
    pid = w.scheduler()
    seen = w.blind().state()
    assert (seen.state, seen.pid, seen.since, seen.detail) == ("unverified", pid, SINCE, "the process table could not be read")


def test_without_a_pidfile_an_unreadable_process_table_changes_nothing(w: StatusWorld) -> None:
    w.no_pidfile()
    assert w.blind().state() == SchedulerState("stopped")


def test_asking_twice_gives_the_same_answer(w: StatusWorld) -> None:
    w.scheduler()
    assert w.status.state() == w.status.state()


# ------------------------------------------------------------------------------ exit reason


def test_a_stopped_scheduler_that_exited_by_itself_says_why(w: StatusWorld) -> None:
    w.mark_exit(FINISHED + "\n")
    assert w.status.exit_reason() == FINISHED
    assert w.status.describe() == f"scheduler: stopped ({FINISHED})"


def test_without_a_marker_there_is_no_reason(w: StatusWorld) -> None:
    assert w.status.exit_reason() == ""


@pytest.mark.parametrize("text", ["", "\n", "  \n  "])
def test_an_empty_marker_is_no_reason(w: StatusWorld, text: str) -> None:
    w.mark_exit(text)
    assert w.status.exit_reason() == ""
    assert w.status.describe() == "scheduler: stopped"


def test_the_reason_is_only_true_while_root_has_no_task_that_was_not_answered(w: StatusWorld) -> None:
    w.mark_exit(FINISHED + "\n")
    w.open_task(True)
    assert w.status.exit_reason() == ""
    assert w.status.describe() == "scheduler: stopped"
    w.open_task(False)
    assert w.status.exit_reason() == FINISHED


def test_the_reason_is_stripped(w: StatusWorld) -> None:
    w.mark_exit('  waiting on you: "Ship it" needs a decision \n\n')
    assert w.status.exit_reason() == 'waiting on you: "Ship it" needs a decision'


# ------------------------------------------------------------------------------ describe a stopped scheduler


WAITING = Waiting('waiting on you: "Rework the report" needs budget (ceo out of runs)', "Your options: send(to=...)")


def test_a_stopped_scheduler_that_nothing_explains_is_described_by_what_waits_for_the_user(w: StatusWorld) -> None:
    w.wait_on_user(WAITING)
    assert w.status.describe() == f"scheduler: stopped ({WAITING.text})"


def test_the_reason_of_the_exit_comes_before_what_waits_for_the_user(w: StatusWorld) -> None:
    w.mark_exit(FINISHED + "\n")
    w.wait_on_user(WAITING)
    assert w.status.describe() == f"scheduler: stopped ({FINISHED})"


def test_a_running_scheduler_is_described_as_running_whatever_else_is_true(w: StatusWorld) -> None:
    pid = w.scheduler()
    w.mark_exit(FINISHED + "\n")
    w.wait_on_user(WAITING)
    assert w.status.describe() == f"scheduler: running (pid {pid}, since {SINCE})"


def test_a_stale_pidfile_is_described_like_no_scheduler(w: StatusWorld) -> None:
    w.gone()
    w.mark_exit(FINISHED + "\n")
    assert w.status.describe() == f"scheduler: stopped ({FINISHED})"
