"""``ChildRegistry``: the schedulers this process started are reaped when they end, so that they never linger as zombies."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.daemon._children import ChildRegistry
from hirearchy.processes import ProcessHandle
from hirearchy.processes.testing import FakeProcessTable


def spawn(table: FakeProcessTable, tmp_path: Path) -> ProcessHandle:
    return table.spawn_detached(["hirearchy", "run"], cwd=tmp_path, env={}, log=tmp_path / "scheduler.log")


def test_a_child_that_ended_is_reaped_when_the_registry_reaps(tmp_path: Path) -> None:
    table = FakeProcessTable()
    children = ChildRegistry()
    handle = spawn(table, tmp_path)
    children.adopt(handle)
    table.exit(handle.pid, 0)
    info = table.info(handle.pid)
    assert info is not None and info.state.startswith("Z")  # an ended child lingers as a zombie ...
    children.reap()
    assert table.info(handle.pid) is None  # ... until its parent has looked


def test_a_child_that_still_runs_is_kept(tmp_path: Path) -> None:
    table = FakeProcessTable()
    children = ChildRegistry()
    running, ended = spawn(table, tmp_path), spawn(table, tmp_path)
    children.adopt(running)
    children.adopt(ended)
    table.exit(ended.pid, 0)
    children.reap()
    assert table.info(ended.pid) is None
    assert table.info(running.pid) is not None
    table.exit(running.pid, 0)
    children.reap()  # it was not forgotten
    assert table.info(running.pid) is None


def test_reaping_without_children_or_twice_is_harmless(tmp_path: Path) -> None:
    table = FakeProcessTable()
    children = ChildRegistry()
    children.reap()
    handle = spawn(table, tmp_path)
    children.adopt(handle)
    table.exit(handle.pid, 0)
    children.reap()
    children.reap()
    assert table.info(handle.pid) is None


def test_the_process_that_was_adopted_is_not_touched_while_it_lives(tmp_path: Path) -> None:
    table = FakeProcessTable()
    children = ChildRegistry()
    handle = spawn(table, tmp_path)
    children.adopt(handle)
    children.reap()
    assert handle.returncode is None and table.signals == []
