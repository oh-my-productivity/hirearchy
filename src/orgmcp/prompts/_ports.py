"""The ports ``prompts`` defines for what it consumes and for the parts its texts are made of (consumer-owned, narrower than the provider's).

The run prompt is composed of small roles - the line of an agent, the quote of a task, the lines about tools and paths, the link from a result to
the task it serves, the tasks held and delegated, the memory - each with one reason to change.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Protocol, runtime_checkable

from ..kernel import Message


@runtime_checkable
class ServiceNames(Protocol):
    def service_names(self, addr: str) -> list[str]:
        """The (non-retired) services ``addr`` offers, by name; root offers none."""
        ...


@runtime_checkable
class TaskQuoter(Protocol):
    def quote(self, m: Message) -> str:
        """The body of a task verbatim, one ``> `` line per line, so that its own headings do not mix with the prompt's; a very long body is cut with
        the real path of the file to read the rest."""
        ...


@runtime_checkable
class AgentLines(Protocol):
    def agent_line(self, addr: str) -> str:
        """``<addr> [<role>] <state>, budget <n>, open tasks <n>, delegated <n>, unread <n>``."""
        ...


@runtime_checkable
class FilesLines(Protocol):
    def lines(self, addr: str, meta: Mapping[str, object]) -> list[str]:
        """The ``Files`` part of the state of ``addr`` (its charter meta is ``meta``): where each kind of path points and which tool reaches it.
        Empty for an agent with no workspace, no inputs and no built-in tools."""
        ...


@runtime_checkable
class UpstreamTasks(Protocol):
    def upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that the delegation ``delegated`` probably serves, with its latest result (None = still open); None when there
        is not exactly one candidate."""
        ...


@runtime_checkable
class ContextRenderer(Protocol):
    def render(self, addr: str, m: Message) -> str:
        """A message of the batch of ``addr`` as it is shown; a result is followed by the task it answers and, when it can be told, the task of
        ``addr`` it probably serves."""
        ...


@runtime_checkable
class HeldTaskLines(Protocol):
    def lines(self, addr: str, shown: Collection[str]) -> list[str]:
        """The bullet lines of the tasks ``addr`` holds: the open ones, and those it reported ``blocked`` (not final). A task in ``shown`` gets a
        pointer to the new messages instead of its quoted text."""
        ...


@runtime_checkable
class DelegationLines(Protocol):
    def lines(self, addr: str) -> list[str]:
        """The bullet lines of the work ``addr`` delegated that is still outstanding, with the state of the report it went to."""
        ...


@runtime_checkable
class MemoryText(Protocol):
    def memory_text(self, addr: str) -> str:
        """The memory of ``addr`` as the prompt shows it: trimmed, ``(empty: ...)`` when there is none, and when it is over the word cap a notice
        asking for it to be condensed."""
        ...


@runtime_checkable
class Briefing(Protocol):
    def briefing(self, addr: str) -> str:
        """What a run of ``addr`` starts from, which does not depend on the run: the rules of the organization, then the charter and the memory
        of ``addr`` under their headings."""
        ...


@runtime_checkable
class RunNotices(Protocol):
    def notices(self, addr: str, batch: Sequence[Message]) -> str:
        """The sections between the state and the new messages: the one-time notice about stray files, then (only for an agent that offers a
        service) the sections of a service owner. Empty when there is nothing to say."""
        ...
