"""Runtime fields of ``agents`` (ARCHITECTURE.md 3.9): one field per port that ``wire_agents.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..agents import AgentDirectory, AgentRegistry, CharterReader, RetiredArchive

STEP: str | None = "A-agents"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    agents: AgentDirectory
    charters: CharterReader
    agent_registry: AgentRegistry  # not ``registry`` (section 6.2): other packages have registries too (runs, strays)
    retired_archive: RetiredArchive
