"""Fakes and the registry the contract suites iterate over.

``FixedStates``, ``NamedServices``, ``FixedSections`` and ``ToldOnce`` are the state words, the offered services, the sections of a service owner
and the stray notice that a test puts in (they are other features' own rules). ``FixedStateSummary``, ``FixedWhoami`` and ``FixedRunPrompt`` are
the texts a consumer (``cli``, the MCP server, the scheduler) is given when its test is not about the prompts. ``disk_world`` and ``memory_world``
are the real prompts over the agents, mailboxes and settings on disk and in memory.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..access import AccessScopes, ToolNaming
from ..access.testing import DEFAULT_ORG_MD, StaticAccess, charters_on_disk
from ..agents import AgentDirectory, CharterReader
from ..agents.testing import fs_agents
from ..budget.testing import FixedBudget
from ..eligibility import AgentStates
from ..kernel import RUNTIME, Message, OrgLayout, OrgPaths, join_frontmatter, norm
from ..mail import MailboxReader
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ..reflection import ServicePromptSections
from ..settings import OrgSettings
from ..settings.testing import fs_org_settings
from ..strays import StrayRegistry
from . import _assembly
from ._ports import (
    AgentLines,
    Briefing,
    ContextRenderer,
    DelegationLines,
    FilesLines,
    HeldTaskLines,
    MemoryText,
    RunNotices,
    ServiceNames,
    TaskQuoter,
    UpstreamTasks,
)
from .api import RunPromptBuilder, StateSummarizer, Whoami


class FixedStates(AgentStates):
    """The state word of an agent is the one in ``words`` (``idle`` for an agent that is not there)."""

    def __init__(self) -> None:
        self.words: dict[str, str] = {}

    def state(self, addr: str) -> str:
        return self.words.get(norm(addr), "idle")


class NamedServices(ServiceNames):
    """The services an agent offers are the names in ``offered`` (none for an agent that is not there); ``asked`` lists whom it was asked about."""

    def __init__(self) -> None:
        self.offered: dict[str, list[str]] = {}
        self.asked: list[str] = []

    def service_names(self, addr: str) -> list[str]:
        self.asked.append(addr)
        return list(self.offered.get(norm(addr), []))


class FixedSections(ServicePromptSections):
    """The sections of a service owner are the text in ``text`` (empty for an agent that is not there); ``asked`` lists who was asked, with the batch."""

    def __init__(self) -> None:
        self.text: dict[str, str] = {}
        self.asked: list[tuple[str, Sequence[Message]]] = []

    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        self.asked.append((addr, batch))
        return self.text.get(addr, "")


class ToldOnce(StrayRegistry):
    """``notices`` holds the notice of an agent until it is taken (told once, like the real registry); ``record`` lists what was recorded."""

    def __init__(self) -> None:
        self.notices: dict[str, str] = {}
        self.recorded: list[tuple[str, tuple[str, ...]]] = []

    def record(self, addr: str, paths: Sequence[str]) -> None:
        self.recorded.append((addr, tuple(paths)))

    def take_notice(self, addr: str) -> str:
        return self.notices.pop(addr, "")


class FixedStateSummary(StateSummarizer):
    """The state summary is exactly ``text``; ``asked`` lists (agent, shown) of every question."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked: list[tuple[str, Collection[str] | None]] = []
        self.on_ask: Callable[[], None] | None = None  # called at every question (a test of the order of things)

    def state_summary(self, addr: str, shown: Collection[str] | None = None) -> str:
        self.asked.append((addr, shown))
        if self.on_ask is not None:
            self.on_ask()
        return self.text


class FixedWhoami(Whoami):
    """The answer is exactly ``text``; ``asked`` lists whom it was asked about."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked: list[str] = []

    def whoami(self, addr: str) -> str:
        self.asked.append(addr)
        return self.text


class FixedRunPrompt(RunPromptBuilder):
    """The prompt is exactly ``text``; ``asked`` lists (agent, batch) of every question."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked: list[tuple[str, Sequence[Message]]] = []

    def run_prompt(self, addr: str, batch: Sequence[Message]) -> str:
        self.asked.append((addr, batch))
        return self.text


class FixedQuote(TaskQuoter):
    """The quote of any task is ``QUOTE``; ``asked`` lists the tasks it was asked to quote."""

    def __init__(self) -> None:
        self.asked: list[Message] = []

    def quote(self, m: Message) -> str:
        self.asked.append(m)
        return "QUOTE"


class FixedUpstream(UpstreamTasks):
    """The upstream task of any delegation is ``found`` (None: none); ``asked`` lists (agent, delegation) of every question."""

    def __init__(self, found: tuple[Message, Message | None] | None = None) -> None:
        self.found = found
        self.asked: list[tuple[str, Message]] = []

    def upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        self.asked.append((addr, delegated))
        return self.found


class FixedFiles(FilesLines):
    """The Files part is ``found``; ``asked`` lists (agent, charter meta) of every question."""

    def __init__(self, found: Sequence[str]) -> None:
        self.found = list(found)
        self.asked: list[tuple[str, Mapping[str, object]]] = []

    def lines(self, addr: str, meta: Mapping[str, object]) -> list[str]:
        self.asked.append((addr, meta))
        return list(self.found)


class FixedAgentLines(AgentLines):
    """The line of an agent is ``AGENT-LINE <addr>``."""

    def agent_line(self, addr: str) -> str:
        return f"AGENT-LINE {addr}"


class FixedHeld(HeldTaskLines):
    """The lines of the tasks held are ``found``; ``asked`` lists (agent, shown) of every question."""

    def __init__(self, found: Sequence[str]) -> None:
        self.found = list(found)
        self.asked: list[tuple[str, Collection[str]]] = []

    def lines(self, addr: str, shown: Collection[str]) -> list[str]:
        self.asked.append((addr, shown))
        return list(self.found)


class FixedDelegations(DelegationLines):
    """The lines of the delegations outstanding are ``found``."""

    def __init__(self, found: Sequence[str]) -> None:
        self.found = list(found)

    def lines(self, addr: str) -> list[str]:
        return list(self.found)


class FixedMemory(MemoryText):
    """The memory text is ``text``; ``asked`` lists whom it was asked about."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked: list[str] = []

    def memory_text(self, addr: str) -> str:
        self.asked.append(addr)
        return self.text


class FixedBriefing(Briefing):
    """The briefing is ``text``; ``asked`` lists whom it was asked about."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked: list[str] = []

    def briefing(self, addr: str) -> str:
        self.asked.append(addr)
        return self.text


class FixedRenderer(ContextRenderer):
    """A message is shown as ``RENDERED <id>``; ``asked`` lists (agent, message) of every question."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, Message]] = []
        self.on_ask: Callable[[], None] | None = None

    def render(self, addr: str, m: Message) -> str:
        self.asked.append((addr, m))
        if self.on_ask is not None:
            self.on_ask()
        return f"RENDERED {m.id}"


class FixedNotices(RunNotices):
    """The notices are ``text``; ``asked`` lists (agent, batch) of every question."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.asked: list[tuple[str, Sequence[Message]]] = []
        self.on_ask: Callable[[], None] | None = None

    def notices(self, addr: str, batch: Sequence[Message]) -> str:
        self.asked.append((addr, batch))
        if self.on_ask is not None:
            self.on_ask()
        return self.text


@dataclass(frozen=True)
class PromptsWorld:
    """The three ports over one organization of agents, mailboxes, budgets, states, services and settings that a test sets."""

    summary: StateSummarizer
    whoami: Whoami
    prompt: RunPromptBuilder
    mail: MailboxReader
    root: Path  # the organization directory as the ports see it
    states: FixedStates
    services: NamedServices
    sections: FixedSections
    strays: ToldOnce
    agent: Callable[[str, Mapping[str, object], str], None]  # (addr, charter meta, charter text): the agent exists
    memory: Callable[[str, str], None]  # the MEMORY.md of the agent has this text
    config: Callable[[str], None]  # ORG.md becomes this text
    budget: Callable[[str, int], None]  # the agent has this many runs left
    send: Callable[..., Message]  # (sender, to, kind, title, body, *, reply_to, status, wake): one more message, in both mailboxes


def _world(
    mail: MailHarness, agents: AgentDirectory, charters: CharterReader, settings: OrgSettings, put_config: Callable[[str], None],
    scopes: AccessScopes, naming: ToolNaming, layout: OrgLayout,
) -> PromptsWorld:
    budgets, states, services, sections, strays = FixedBudget(mail.tasks, agents, charters), FixedStates(), NamedServices(), FixedSections(), ToldOnce()
    numbers = itertools.count(1)

    def agent(addr: str, meta: Mapping[str, object], charter: str) -> None:
        mail.put(f"{addr}/AGENT.md", join_frontmatter(dict(meta), charter))

    def send(
        sender: str, to: str, kind: str, title: str, body: str, *, reply_to: str | None = None, status: str | None = None, wake: bool = True,
    ) -> Message:
        stamp = next(numbers)
        msg = Message(
            sender=sender, to=to, type=kind, title=title, body=body, reply_to=reply_to, status=status, wake=wake,
            id=f"20260101T000000{stamp:06d}-{norm(sender).replace('/', '-')}-aaaa", created="2026-01-01T00:00:00+00:00",
        )
        mail.writer.store(msg)
        return msg

    def budget(addr: str, runs: int) -> None:
        budgets.held[norm(addr)] = runs

    summary = _assembly.state_summarizer(agents, charters, mail.reader, mail.tasks, budgets, states, scopes, naming, layout)
    run = _assembly.run_prompt_builder(agents, charters, settings, mail.reader, naming, strays, services, sections, layout, summary)
    return PromptsWorld(
        summary, _assembly.whoami(agents, charters, summary), run, mail.reader, layout.root, states, services, sections, strays,
        agent, lambda addr, text: mail.put(f"{addr}/MEMORY.md", text), put_config, budget, send,
    )


def disk_world(tmp_path: Path) -> PromptsWorld:
    disk, access, document = fs_agents(tmp_path), charters_on_disk(tmp_path), fs_org_settings(tmp_path)
    document.put(DEFAULT_ORG_MD)
    return _world(
        fs_mailbox(tmp_path), disk.directory, disk.charters, document.settings, document.put, access.scopes, access.naming, OrgPaths(tmp_path),
    )


def memory_world(tmp_path: Path) -> PromptsWorld:
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    access = StaticAccess(agents=box.agents)
    return _world(mail, box.agents, box.agents, access.settings, access.put_config, access, access, OrgPaths(box.agents.root))


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    StateSummarizer: [disk_world, memory_world],
    Whoami: [disk_world, memory_world],
    RunPromptBuilder: [disk_world, memory_world],
}
