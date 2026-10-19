"""The ports the views are made of, owned by the package (not part of its api): the history of the messages, the derivation of a message's
trace, and the runs. Each has one implementation in the package; the views take them by these types so that a test puts a fake in."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..kernel import JsonObject

if TYPE_CHECKING:
    from ._messages import Msg
    from ._runs import RunRec


@runtime_checkable
class MessageHistory(Protocol):
    def messages(self) -> dict[str, Msg]:
        """Every message of the organization once, by id: the front matter of the first copy, every copy's ``(owner, box)``. Files that do not
        parse are left out."""
        ...


@runtime_checkable
class TraceDeriver(Protocol):
    def of(self, mid: str) -> tuple[str | None, str]:
        """``(trace id or None, source)`` of a message; the source is ``recorded``, ``derived:<rule>`` or ``unknown``."""
        ...


@runtime_checkable
class TraceDerivers(Protocol):
    def derive(self, msgs: Mapping[str, Msg], batches: Mapping[str, list[str]] | None = None) -> TraceDeriver:
        """A deriver over these messages; ``batches`` maps a run id to the ids it was started with (from ``run.start`` events)."""
        ...


@runtime_checkable
class RunCollection(Protocol):
    def collect(
        self,
        since: datetime | None,
        until: datetime | None,
        events: Mapping[str, Mapping[str, JsonObject]] | None = None,
        agents: Sequence[str] | None = None,
    ) -> list[RunRec]:
        """Every run that STARTED in ``[since, until]``, oldest first: the run logs of the live agents (the file truth: one log = one run = one
        run of budget), completed with ``run.start`` / ``run.end`` events where there are some, plus (with no ``agents`` given) the runs known
        only from events, of agents that were retired since. ``events`` is ``run_events`` of the window, read when not given."""
        ...

    def team_runs(
        self, team: Sequence[str], in_windows: Callable[[str], bool], events: Mapping[str, Mapping[str, JsonObject]]
    ) -> list[RunRec]:
        """The runs of the agents of ``team`` whose log stem ``in_windows`` accepts, oldest first (the runs of one request)."""
        ...
