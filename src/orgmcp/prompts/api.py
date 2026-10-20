"""The public surface of ``prompts``: the texts an agent is shown.

Everything here is DERIVED from the other features' ports at the moment of the call - the charter and the memory, the tasks open, blocked and
delegated, the budget and the state of the agent and of its reports, the tools and the paths it was granted, the messages of the run - and nothing
is stored. The wording is part of the protocol the agents follow, so it does not change with the code that makes it: a prompt is byte for byte what
it was.

The parts the texts are made of that the facade hands out one by one (``Org._agent_line``, ``_quote``, ``_files_lines``, ``_render_in_context``,
``_upstream``) are ports too: ``AgentLines``, ``TaskQuoter``, ``FilesLines``, ``ContextRenderer`` and ``UpstreamTasks``.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Protocol, runtime_checkable

from ..kernel import Message
from ._ports import AgentLines, ContextRenderer, FilesLines, TaskQuoter, UpstreamTasks

__all__ = [
    "AgentLines",
    "ContextRenderer",
    "FilesLines",
    "RunPromptBuilder",
    "StateSummarizer",
    "TaskQuoter",
    "UpstreamTasks",
    "Whoami",
]


@runtime_checkable
class StateSummarizer(Protocol):
    def state_summary(self, addr: str, shown: Collection[str] | None = None) -> str:
        """The situation of ``addr`` as bullet lines: address, parent and role; (not for root) budget, hiring, tools and the ``Files`` part; direct reports,
        siblings, the tasks open (their text quoted verbatim, cut when very long), those reported ``blocked`` and the delegations still outstanding.

        ``shown``: ids of tasks whose full text the caller prints elsewhere (the new messages of a run): they get a pointer instead of the quote.
        Raises ``OrgError`` for an agent that does not exist."""
        ...


@runtime_checkable
class Whoami(Protocol):
    def whoami(self, addr: str) -> str:
        """The state summary of ``addr``, then ``## Charter`` and its charter (root: ``(root has no charter)``). Raises ``OrgError`` for an agent
        that does not exist."""
        ...


@runtime_checkable
class RunPromptBuilder(Protocol):
    def run_prompt(self, addr: str, batch: Sequence[Message]) -> str:
        """The whole prompt of one run of ``addr`` over ``batch``: the rules, the charter, the memory (with the notice when it is over the cap), the state,
        the one-time notice about stray files, the sections of a service owner, and every message of the batch (a result followed by the task it
        answers). Raises ``OrgError`` for an agent that does not exist."""
        ...
