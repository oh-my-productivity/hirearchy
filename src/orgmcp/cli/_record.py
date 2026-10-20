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
        try:
            if args.cmd in ("mcp", "dash"):  # a long-lived server records its tool calls itself; the dashboard is read-only
                return
            root = Path(args.path).expanduser().resolve() if args.cmd == "init" else self._session.named(args)
            error = None
            if failure is not None:
                error = str(failure) or type(failure).__name__
            self._sinks.for_root(root).emit(
                "cli.command", actor=ROOT, run=None, trace=None, proc="cli", command=args.cmd, ok=failure is None,
                ms=round((self._clock.monotonic() - started) * 1000, 2),
                error=clip(error, ERROR_MAX) if error else None,
                error_type=type(failure).__name__ if failure is not None else None,
            )
        except Exception:  # noqa: BLE001
            pass
