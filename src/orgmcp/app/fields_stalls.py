"""Runtime fields of ``stalls`` (ARCHITECTURE.md 3.27): one field per port that ``wire_stalls.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..stalls import NudgeLedger, StallLadder

STEP: str | None = "C-stalls"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    stall_ladder: StallLadder
    nudge_ledger: NudgeLedger
