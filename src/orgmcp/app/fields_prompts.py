"""Runtime fields of ``prompts`` (ARCHITECTURE.md 3.24): one field per port that ``wire_prompts.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..prompts import RunPromptBuilder, StateSummarizer, Whoami

STEP: str | None = "C-prompts"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    state_summarizer: StateSummarizer
    agent_whoami: Whoami  # not ``whoami``: the name of a verb the facade has
    run_prompt_builder: RunPromptBuilder
