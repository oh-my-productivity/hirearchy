"""Runtime fields of ``processes`` (ARCHITECTURE.md 3.8): one field per port that ``wire_processes.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner

STEP: str | None = "A-processes"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {
    "ProcessHandle": "a value that ProcessSpawner.spawn returns for each process, not a port that is built once",
}


@dataclass(frozen=True)
class Fields:
    process_spawner: ProcessSpawner
    process_inspector: ProcessInspector
    process_signaller: ProcessSignaller
    orphan_judge: OrphanJudge
