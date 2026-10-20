"""The program: the parser of the commands, the run of one, its record."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ..kernel import Clock, OrgError
from ..telemetry import ProcessLabel
from ._ports import Command, CommandRecording, Output
from .api import CliApp


class ArgparseCliApp(CliApp):
    """``orgmcp [--root DIR] COMMAND ...``: every command adds its sub-parser (in this order), the chosen one runs, and its end is recorded (``cli.command``)."""

    def __init__(self, commands: Sequence[Command], recorder: CommandRecording, label: ProcessLabel, clock: Clock, out: Output) -> None:
        self._commands = list(commands)
        self._recorder = recorder
        self._label = label
        self._clock = clock
        self._out = out

    def parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(prog="orgmcp", description="A file-based organization of agents, run over MCP.")
        p.add_argument("--root", help="organization directory (default: $ORG_ROOT or nearest dir with ORG.md)")
        sub = p.add_subparsers(dest="cmd", required=True)
        for command in self._commands:
            command.add_arguments(sub)
        return p

    def main(self, argv: Sequence[str] | None = None) -> None:
        args = self.parser().parse_args(argv)
        self._label.set("cli")
        started = self._clock.monotonic()
        try:
            args.fn(args)
        except OrgError as exc:
            self._recorder.record(args, started, exc)
            self._out.warn(f"error: {exc}")
            raise SystemExit(1)
        except SystemExit as exc:  # a command that exits by itself (e.g. plan with errors): a non-zero code is a failure
            self._recorder.record(args, started, None if exc.code in (None, 0) else RuntimeError(f"exit {exc.code}"))
            raise
        except BaseException as exc:
            self._recorder.record(args, started, exc)
            raise
        else:
            self._recorder.record(args, started, None)
