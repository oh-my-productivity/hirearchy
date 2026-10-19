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
ERROR_MAX = 500
F = TypeVar('F', bound=Callable[..., Any])

class BatchCallTrace(CallTrace):
    """The trace of a call: that of the message it delivered, else of the message it names, else the one trace of the caller's batch."""

    def __init__(self, setup: SetupMode, lookup: Provider[TraceLookup], directory: Provider[AgentDirectory], mail: Provider[MailboxReader]) -> None:
        raise NotImplementedError('red: D-mcp')

    def of(self, me: str, arguments: Mapping[str, object], seen: Sequence[str | None]) -> str | None:
        raise NotImplementedError('red: D-mcp')

class ToolCallRecorder(ToolRecorder):
    """Wraps ``mcp.tool`` once, before any group registers: every tool registered through it afterwards, by a group or by anyone later, emits a
    ``tool.call`` event (ok or refused/failed, with its duration and an argument summary without bodies). Name, signature and docstring are those
    of the tool; the outcome is unchanged.

    The traces a call delivered are collected in the thread that runs the wrapper (``TraceScope`` is per thread): the ``progress`` tool works in a
    worker thread, so what it delivers is not collected (kept exactly as it always was)."""

    def __init__(self, binding: OrgBindingPort, sinks: EventSinks, scope: TraceScope, summarizer: ArgumentSummarizer, trace: CallTrace) -> None:
        raise NotImplementedError('red: D-mcp')

    def instrument(self, mcp: FastMCP, me: str) -> None:
        raise NotImplementedError('red: D-mcp')

    def _recorded(self, fn: F, tool: str, me: str) -> F:
        raise NotImplementedError('red: D-mcp')

    def _record(self, me: str, tool: str, sig: inspect.Signature, args: tuple[Any, ...], kwargs: dict[str, Any], started: float, exc: BaseException | None, seen: list[str | None]) -> None:
        """Emit the ``tool.call`` event of one finished call. Never raises."""
        raise NotImplementedError('red: D-mcp')
