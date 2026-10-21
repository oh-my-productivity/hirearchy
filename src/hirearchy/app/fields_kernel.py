"""Runtime fields of ``kernel`` (ARCHITECTURE.md 3.1): one field per port that ``wire_kernel.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..kernel import AtomicWriter, Clock, Environment, EventSink, IdGenerator, LedgerStore, OrgLayout, TokenSource, TraceTap

STEP: str | None = "M2"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    paths: OrgLayout
    clock: Clock
    tokens: TokenSource
    ids: IdGenerator
    atomic_writer: AtomicWriter
    ledgers: LedgerStore
    environment: Environment
    events: EventSink  # provided by wire_telemetry (the real sink is telemetry's)
    trace_tap: TraceTap  # provided by wire_telemetry (the real tap is telemetry's)
