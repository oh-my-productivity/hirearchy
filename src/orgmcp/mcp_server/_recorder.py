"""The ``tool.call`` event of every tool call, and the request a call belongs to."""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from ..agents import AgentDirectory
from ..kernel import ROOT, Provider, clip, single
from ..mail import MailboxReader
from ..telemetry import ArgumentSummarizer, EventSinks, TraceScope
from ..traces import TraceLookup
from ._ports import CallTrace, SetupMode, ToolRecorder
from .api import OrgBindingPort

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

ERROR_MAX = 500  # the longest error text that goes into an event

F = TypeVar("F", bound=Callable[..., Any])


class BatchCallTrace(CallTrace):
    """The trace of a call: that of the message it delivered, else of the message it names, else the one trace of the caller's batch."""

    def __init__(self, setup: SetupMode, lookup: Provider[TraceLookup], directory: Provider[AgentDirectory], mail: Provider[MailboxReader]) -> None:
        self._setup = setup
        self._lookup = lookup
        self._directory = directory
        self._mail = mail

    def of(self, me: str, arguments: Mapping[str, object], seen: Sequence[str | None]) -> str | None:
        trace = single(seen)
        if trace or self._setup.active():
            return trace
        for key in ("task_id", "reply_to", "revises"):
            value = arguments.get(key)
            if isinstance(value, str) and (trace := self._lookup().trace_of(me, value)):
                return trace
        if me != ROOT and self._directory().exists(me):
            return single(m.trace for m in self._mail().messages(me, "inflight"))
        return None


class ToolCallRecorder(ToolRecorder):
    """Wraps ``mcp.tool`` once, before any group registers: every tool registered through it afterwards, by a group or by anyone later, emits a
    ``tool.call`` event (ok or refused/failed, with its duration and an argument summary without bodies). Name, signature and docstring are those
    of the tool; the outcome is unchanged.

    The traces a call delivered are collected in the thread that runs the wrapper (``TraceScope`` is per thread): the ``progress`` tool works in a
    worker thread, so what it delivers is not collected (kept exactly as it always was)."""

    def __init__(self, binding: OrgBindingPort, sinks: EventSinks, scope: TraceScope, summarizer: ArgumentSummarizer, trace: CallTrace) -> None:
        self._binding = binding
        self._sinks = sinks
        self._scope = scope
        self._summarizer = summarizer
        self._trace = trace

    def instrument(self, mcp: FastMCP, me: str) -> None:
        register = mcp.tool

        def tool(*args: Any, **kwargs: Any) -> Callable[[F], Any]:
            decorate = register(*args, **kwargs)
            named = kwargs.get("name") or (args[0] if args and isinstance(args[0], str) else None)

            def wrap(fn: F) -> Any:
                return decorate(self._recorded(fn, named or fn.__name__, me))

            return wrap

        mcp.tool = tool  # type: ignore[method-assign]

    def _recorded(self, fn: F, tool: str, me: str) -> F:
        sig = inspect.signature(fn)

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                started, failure = time.perf_counter(), None
                with self._scope.collect() as seen:
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as exc:
                        failure = exc
                        raise
                    finally:
                        self._record(me, tool, sig, args, kwargs, started, failure, seen)
        else:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                started, failure = time.perf_counter(), None
                with self._scope.collect() as seen:
                    try:
                        return fn(*args, **kwargs)
                    except Exception as exc:
                        failure = exc
                        raise
                    finally:
                        self._record(me, tool, sig, args, kwargs, started, failure, seen)
        return wrapper  # type: ignore[return-value]

    def _record(self, me: str, tool: str, sig: inspect.Signature, args: tuple[Any, ...], kwargs: dict[str, Any], started: float,
                exc: BaseException | None, seen: list[str | None]) -> None:
        """Emit the ``tool.call`` event of one finished call. Never raises."""
        try:
            root = self._binding.root
            if root is None:
                return
            try:
                arguments = dict(sig.bind_partial(*args, **kwargs).arguments)
            except TypeError:
                arguments = dict(kwargs)
            try:
                trace = self._trace.of(me, arguments, seen)
            except Exception:  # noqa: BLE001
                trace = None
            self._sinks.for_root(root).emit(
                "tool.call", proc="mcp", actor=me, trace=trace, tool=tool, ok=exc is None,
                ms=round((time.perf_counter() - started) * 1000, 2),
                error=clip(str(exc) or type(exc).__name__, ERROR_MAX) if exc is not None else None,
                error_type=type(exc).__name__ if exc is not None else None,
                args=self._summarizer.summarize(arguments),
            )
        except Exception:  # noqa: BLE001 - recording a call must never change its outcome
            pass
