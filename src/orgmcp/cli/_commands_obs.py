"""``orgmcp obs now|trace|metrics|events`` and ``orgmcp check``: the command line of the read-only views of the observability."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import cast

from ..kernel import Clock, JsonObject, Provider
from ..observability import EventQueries, IntegrityChecks, MetricQueries, NowQueries, ObservabilityRenderer, TraceQueries, format_event
from ._ports import Arguments, Command, EventTails, JsonDump, OrgSession, Output, Terminal


class NowCommand(Command):
    def __init__(
        self, session: OrgSession, queries: Provider[NowQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, terminal: Terminal,
        clock: Clock, out: Output,
    ) -> None:
        self._session = session
        self._queries = queries
        self._renderer = renderer
        self._dump = dump
        self._terminal = terminal
        self._clock = clock
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class TraceCommand(Command):
    def __init__(self, session: OrgSession, traces: Provider[TraceQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._traces = traces
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class MetricsCommand(Command):
    def __init__(self, session: OrgSession, metrics: Provider[MetricQueries], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._metrics = metrics
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class EventsCommand(Command):
    def __init__(
        self, session: OrgSession, events: Provider[EventQueries], renderer: Provider[ObservabilityRenderer], tails: Provider[EventTails], dump: JsonDump,
        clock: Clock, out: Output,
    ) -> None:
        self._session = session
        self._events = events
        self._renderer = renderer
        self._tails = tails
        self._dump = dump
        self._clock = clock
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class ObsCommand(Command):
    """``obs``: the views of the observability, each a command of its own."""

    def __init__(self, views: Sequence[Command]) -> None:
        self._views = list(views)

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class CheckCommand(Command):
    def __init__(self, session: OrgSession, checks: Provider[IntegrityChecks], renderer: Provider[ObservabilityRenderer], dump: JsonDump, out: Output) -> None:
        self._session = session
        self._checks = checks
        self._renderer = renderer
        self._dump = dump
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
