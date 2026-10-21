"""Process-scope resources: what the module globals were, created once per process (ARCHITECTURE.md 2.4)."""

from __future__ import annotations

from pathlib import Path

from ..daemon._children import ChildRegistry
from ..kernel import EventSink
from ..kernel._system import SystemClock
from ..mail._index import StampCachedMetaReader
from ..mail._parser import CachingMessageParser
from ..telemetry._label import MutableProcessLabel
from ..telemetry._pool import EventWriterPool
from ..telemetry._sink import FsEventSinks
from ..telemetry._trace_scope import ThreadLocalTraceScope


class ProcessResources:
    """The objects that exist once per process and are shared by every organization runtime in it."""

    def __init__(
        self,
        message_parser: CachingMessageParser,
        meta_cache: StampCachedMetaReader | None = None,
        event_pool: EventWriterPool | None = None,
        process_label: MutableProcessLabel | None = None,
        trace_scope: ThreadLocalTraceScope | None = None,
        event_sinks: FsEventSinks | None = None,
        children: ChildRegistry | None = None,
    ) -> None:
        self.message_parser = message_parser  # the 50 000-entry parse cache (the former ``core._PARSED``)
        self.meta_cache = meta_cache or StampCachedMetaReader()  # the 50 000-entry front-matter cache (the former ``observe._META_CACHE``)
        self.event_pool = event_pool or EventWriterPool(SystemClock())  # the open event files of the process and its drop counter
        self.process_label = process_label or MutableProcessLabel()  # which process this is: scheduler, mcp or cli
        self.trace_scope = trace_scope or ThreadLocalTraceScope()  # the traces delivered by the tool call of a thread
        self.event_sinks = event_sinks or FsEventSinks(self.event_pool, self._runtime_events)  # the sink of each root, for callers without a runtime
        self.children = children or ChildRegistry()  # the schedulers this process started (the former ``scheduler._children``); never reset: it only reaps

    def _runtime_events(self, root: Path) -> EventSink:
        from .wiring import open_runtime  # late: wiring imports this module

        return open_runtime(root, {ProcessResources: self}).events

    def reset(self) -> None:
        """Empty every resource (tests start from a clean process); the objects themselves stay."""
        self.message_parser.clear()
        self.meta_cache.clear()
        self.event_pool.reset()
        self.process_label.set("cli")
        self.event_sinks.reset()
