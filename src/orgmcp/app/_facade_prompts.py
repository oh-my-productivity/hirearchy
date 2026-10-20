"""The texts an agent is shown: whoami, state summary, run prompt (prompts).

``state_summary``, ``whoami`` and ``run_prompt`` call the ports of ``self.runtime`` (step C-prompts; ARCHITECTURE.md 5.3 and 6.4). ``_agent_line``,
``_indent``, ``_quote``, ``_files_lines``, ``_render_in_context`` and ``_upstream`` are the old spellings of the parts those texts are made of
(nothing calls them any more; the signature guard keeps them): the ports ``agent_lines``, ``task_quoter``, ``files_lines``, ``context_renderer`` and
``upstream_tasks`` of the runtime, and the function ``indent`` (static, as it always was)."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from ..kernel import Message
from ..prompts._text import indent
from .runtime import OrgRuntime


class PromptsMixin:
    """The texts an agent is shown: whoami, state summary, run prompt (prompts)."""

    runtime: OrgRuntime

    def _agent_line(self, addr: str) -> str:
        return self.runtime.agent_lines.agent_line(addr)

    @staticmethod
    def _indent(text: str, n: int) -> str:
        return indent(text, n)

    def _quote(self, m: Message) -> str:
        """Quote a task's body verbatim, so its own headings do not mix with the prompt's structure.

        A very long body is cut like ``Message.render`` does, with the real path of the file to read the rest."""
        return self.runtime.task_quoter.quote(m)

    def state_summary(self, addr: str, shown: Collection[str] | None = None) -> str:
        """The agent's situation. ``shown``: ids of tasks whose full text the caller already prints elsewhere."""
        return self.runtime.state_summarizer.state_summary(addr, shown)

    def _files_lines(self, addr: str, meta: Mapping[str, object]) -> list[str]:
        """The "Files" part of an agent's state: where each kind of path points, and which tool reaches it (empty for an agent with no
        workspace, no inputs and no built-in tools)."""
        return self.runtime.files_lines.lines(addr, meta)

    def whoami(self, addr: str) -> str:
        return self.runtime.agent_whoami.whoami(addr)

    def _render_in_context(self, addr: str, m: Message) -> str:
        """A batch message; a result is followed by the task it answers, so it is judged against what was asked."""
        return self.runtime.context_renderer.render(addr, m)

    def _upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that a delegation probably serves, with its latest result (None = still open)."""
        return self.runtime.upstream_tasks.upstream(addr, delegated)

    def run_prompt(self, addr: str, batch: Sequence[Message]) -> str:
        return self.runtime.run_prompt_builder.run_prompt(addr, batch)
