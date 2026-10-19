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
        raise NotImplementedError

    def main(self, argv: Sequence[str] | None = None) -> None:
        raise NotImplementedError
