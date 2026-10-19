"""Doubles for the unit tests of the pipeline: each is the port it stands for, and all write to one shared log, so that a test can say in which
order things happened (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from orgmcp.kernel import Clock, EventSink, IdGenerator, Message, TraceTap
from orgmcp.mail import MailboxWriter
from orgmcp.traces import TraceStamper

Log = list[str]


class LoggingStamper(TraceStamper):
    """Stamps a scripted trace; remembers what the message looked like when it was asked."""

    def __init__(self, log: Log, trace: str | None = "T1", rule: str = "link", candidates: list[str] | None = None) -> None:
        self._log = log
        self.trace = trace
        self.rule = rule
        self.candidates = candidates or []
        self.saw: list[tuple[str, str]] = []  # (id, created) at the time of the call

    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        self._log.append("stamp")
        self.saw.append((msg.id, msg.created))
        msg.trace = self.trace
        return self.rule, list(self.candidates)


class FailingStamper(TraceStamper):
    def __init__(self, log: Log, error: Exception | None = None) -> None:
        self._log = log
        self._error = error or RuntimeError("the lookup is broken")

    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        self._log.append("stamp")
        raise self._error


class LoggingMailbox(MailboxWriter):
    """Keeps what it is asked to store; remembers the trace the message had at that moment."""

    def __init__(self, log: Log, fails: Exception | None = None) -> None:
        self._log = log
        self._fails = fails
        self.stored: list[Message] = []
        self.traces_seen: list[str | None] = []

    def store(self, msg: Message) -> None:
        self._log.append("store")
        self.traces_seen.append(msg.trace)
        if self._fails is not None:
            raise self._fails
        self.stored.append(msg)


class LoggingTap(TraceTap):
    def __init__(self, log: Log) -> None:
        self._log = log
        self.notes: list[str | None] = []

    def note(self, trace: str | None) -> None:
        self._log.append("note")
        self.notes.append(trace)


@dataclass
class LoggedEvent:
    """One emitted event: the arguments of ``emit``, the free fields in the order given."""

    kind: str
    actor: str | None
    trace: str | None
    fields: dict[str, object]


class LoggingEvents(EventSink):
    def __init__(self, log: Log) -> None:
        self._log = log
        self.events: list[LoggedEvent] = []

    def emit(
        self,
        kind: str,
        /,
        *,
        actor: str | None = None,
        run: str | None = None,
        trace: str | None = None,
        proc: str | None = None,
        **fields: object,
    ) -> None:
        self._log.append("emit")
        self.events.append(LoggedEvent(kind, actor, trace, fields))


class CountingClock(Clock):
    """A clock at a fixed time that logs every ``now``."""

    def __init__(self, log: Log, at: datetime = datetime(2030, 5, 6, 7, 8, 9, 123456, tzinfo=timezone.utc)) -> None:
        self._log = log
        self._at = at
        self.calls = 0

    def now(self) -> datetime:
        self._log.append("clock")
        self.calls += 1
        return self._at

    def time(self) -> float:
        return self._at.timestamp()

    def monotonic(self) -> float:
        return 0.0

    def sleep(self, seconds: float) -> None:
        pass


class CountingIds(IdGenerator):
    def __init__(self, log: Log, make: Callable[[str], str] = lambda sender: f"ID-{sender}") -> None:
        self._log = log
        self._make = make
        self.asked: list[str] = []

    def message_id(self, sender: str) -> str:
        self._log.append("id")
        self.asked.append(sender)
        return self._make(sender)


class GivenStamper(TraceStamper):
    """The one rule that matters to ``notify``: a trace that is set is kept (``given``), else the message is ambiguous."""

    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        return ("given", []) if msg.trace else ("ambiguous", [])
