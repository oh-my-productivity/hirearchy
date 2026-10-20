"""Runtime fields of ``runs`` (ARCHITECTURE.md 3.11): one field per port that ``wire_runs.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..runs import RunLogReader, RunLogWriter, RunRegistry

STEP: str | None = "A-runs"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "RunLogSink": "a value that RunLogWriter.open_sink returns for each log, not a port that is built once",
}


@dataclass(frozen=True)
class Fields:
    run_log_writer: RunLogWriter
    run_log_reader: RunLogReader
    run_registry: RunRegistry
