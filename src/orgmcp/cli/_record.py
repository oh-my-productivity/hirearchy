"""The ``cli.command`` event of a finished command."""

from __future__ import annotations

from pathlib import Path

from ..kernel import ROOT, Clock, clip
from ..telemetry import EventSinks
from ._ports import Arguments, CommandRecording, OrgSession

ERROR_MAX = 500  # the longest error text that goes into an event


class EventCommandRecorder(CommandRecording):
    """Writes ``cli.command`` (command, ok, ms, error, error_type) into the event log of the organization the command was about to work on."""

    def __init__(self, sinks: EventSinks, session: OrgSession, clock: Clock) -> None:
        self._sinks = sinks
        self._session = session
        self._clock = clock

    def record(self, args: Arguments, started: float, failure: BaseException | None) -> None:
        raise NotImplementedError
