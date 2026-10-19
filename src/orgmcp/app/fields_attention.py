"""Runtime fields of ``attention`` (ARCHITECTURE.md 3.28): one field per port that ``wire_attention.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..attention import HumanQueue, OpenWork, WaitingOnUser

STEP: str | None = "C-attention"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    waiting_on_user: WaitingOnUser
    human_queue: HumanQueue
    open_work: OpenWork
