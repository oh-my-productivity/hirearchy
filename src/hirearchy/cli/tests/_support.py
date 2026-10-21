"""Running a command the way the program does: its own sub-parser makes the arguments, ``fn`` runs them."""

from __future__ import annotations

import argparse
from pathlib import Path

from hirearchy.cli._commands_obs import ObsCommand
from hirearchy.cli._ports import Arguments, Command
from hirearchy.cli.testing import MemoryOutput, ScriptedOrgSession


def parse(command: Command, *argv: str, root: str | None = None) -> Arguments:
    """The arguments of ``hirearchy [--root ROOT] <argv>`` where ``argv`` starts with the name of ``command``."""
    parser = argparse.ArgumentParser(prog="hirearchy")
    parser.add_argument("--root")
    sub = parser.add_subparsers(dest="cmd", required=True)
    command.add_arguments(sub)
    return parser.parse_args([*(["--root", root] if root else []), *argv])


def go(command: Command, *argv: str, root: str | None = None) -> Arguments:
    """Parse and run; returns the arguments."""
    args = parse(command, *argv, root=root)
    args.fn(args)
    return args


def view(command: Command, *argv: str) -> Arguments:
    """A view of ``obs``: parsed under ``obs``, run."""
    args = parse(ObsCommand([command]), "obs", *argv)
    args.fn(args)
    return args


class Fixture:
    """A session of an organization at ``tmp/org`` and the output."""

    def __init__(self, tmp_path: Path, exists: bool = True) -> None:
        self.out = MemoryOutput()
        self.session = ScriptedOrgSession(tmp_path / "org", exists)
