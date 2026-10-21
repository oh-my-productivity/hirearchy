"""``VenvSchedulerCommand``: the program is the ``hirearchy`` script of the interpreter's directory when there is one, else ``python -m hirearchy``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.daemon._command import VenvSchedulerCommand
from hirearchy.kernel import OrgPaths


def test_the_console_script_next_to_the_interpreter_is_the_program(tmp_path: Path) -> None:
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "hirearchy").write_text("#!/bin/sh\n")
    command = VenvSchedulerCommand(OrgPaths(tmp_path / "org"), str(bin_dir / "python"))
    assert command.argv(None, False) == [str(bin_dir / "hirearchy"), "--root", str(tmp_path / "org"), "run"]


def test_without_the_script_the_interpreter_runs_the_module(tmp_path: Path) -> None:
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    command = VenvSchedulerCommand(OrgPaths(tmp_path / "org"), str(bin_dir / "python"))
    assert command.argv(2, True) == [str(bin_dir / "python"), "-m", "hirearchy", "--root", str(tmp_path / "org"), "run", "--max-runs", "2", "--until-done"]


def test_the_script_is_looked_for_every_time(tmp_path: Path) -> None:
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    command = VenvSchedulerCommand(OrgPaths(tmp_path / "org"), str(bin_dir / "python"))
    assert command.argv(None, False)[1] == "-m"
    (bin_dir / "hirearchy").write_text("#!/bin/sh\n")
    assert command.argv(None, False)[0] == str(bin_dir / "hirearchy")
