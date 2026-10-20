"""Runtime fields of ``eligibility`` (ARCHITECTURE.md 3.12): one field per port that ``wire_eligibility.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..eligibility import AgentStates, FailureCounter, PauseStore, RunnableQuery

STEP: str | None = "B-eligibility"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    pause_store: PauseStore
    failure_counter: FailureCounter
    agent_states: AgentStates
    runnable_query: RunnableQuery
