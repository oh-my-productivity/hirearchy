"""``TextRunPromptBuilder``: the whole prompt of one run (moved from ``Org.run_prompt``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..access import ToolNaming
from ..agents import AgentDirectory
from ..kernel import Message
from ._ports import Briefing, ContextRenderer, RunNotices
from .api import RunPromptBuilder, StateSummarizer


class TextRunPromptBuilder(RunPromptBuilder):
    def __init__(
        self, agents: AgentDirectory, briefing: Briefing, summary: StateSummarizer, renderer: ContextRenderer, naming: ToolNaming,
        notices: RunNotices,
    ) -> None:
        self._agents = agents
        self._briefing = briefing
        self._summary = summary
        self._renderer = renderer
        self._naming = naming
        self._notices = notices

    def run_prompt(self, addr: str, batch: Sequence[Message]) -> str:
        raise NotImplementedError("red: C-prompts")
