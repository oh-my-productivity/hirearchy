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
        a = self._agents.require(addr)
        briefing = self._briefing.briefing(a)
        messages = "\n".join(self._renderer.render(a, m) for m in batch) or "(none)"
        shown = {m.id for m in batch if m.type == "task"}
        wn = self._naming.tool_names(a)["write"]
        notice = self._notices.notices(a, batch)
        return f"""# orgmcp run: you are `{a}`

{briefing}

# Your state
{self._summary.state_summary(a, shown)}
- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `{a}/`.
{notice}
# New messages for this run ({len(batch)})
{messages}
---
Handle every new message above with the orgmcp tools, following the protocol.
Messages may be redelivered after a crash: if your state shows one was already handled, skip it.
Before you stop, update your memory with `@orgmcp/{wn}`(path="{a}/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`). Do not wait for replies; end the run when done.
"""
