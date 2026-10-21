"""Fakes and the registry the contract suite iterates over.

``FixedStates`` and ``NamedServices`` are the state words and the offered services a test puts in. ``FixedOrgTree`` is the tree a consumer
(``cli``, the MCP server) is given when its test is not about the tree. ``disk_world`` and ``memory_world`` are the real ``TextOrgTree`` over the
mailboxes and agents on disk and in memory; the budgets, states and services are the ones a test sets (they are other features' own rules).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents import AgentDirectory, CharterReader
from ..agents.testing import fs_agents
from ..budget.testing import FixedBudget
from ..eligibility import AgentStates
from ..kernel import RUNTIME, Message, norm
from ..mail.testing import MailHarness, MemoryMailbox, fs_mailbox, memory_mailbox
from ._ports import ServiceNames
from ._tree import TextOrgTree
from .api import OrgTree


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


class FixedOrgTree(OrgTree):
    """The tree is exactly ``text``."""

    def __init__(self, text: str) -> None:
        self.text = text

    def tree(self) -> str:
        return self.text


@dataclass(frozen=True)
class OverviewWorld:
    """``OrgTree`` over one organization of agents, mailboxes, budgets, states and services that a test sets."""

    tree: OrgTree
    services: NamedServices  # the services the agents offer (``services.offered``), and whom the tree asked about
    agent: Callable[[str, str | None], None]  # (addr, role): the agent exists, with this role (None: its charter says none)
    mail_to: Callable[[str, bool], None]  # (addr, wakes): one more message in the inbox
    delegate: Callable[[str, str, bool], None]  # (sender, to, wakes): a task from sender to ``to`` that is not answered
    set_budget: Callable[[str, int], None]  # the agent has this many runs left
    set_state: Callable[[str, str], None]  # the state word of the agent
    offer: Callable[[str, Sequence[str]], None]  # the agent offers these services


def _world(mail: MailHarness, agents: AgentDirectory, charters: CharterReader) -> OverviewWorld:
    budgets, states, services = FixedBudget(mail.tasks, agents, charters), FixedStates(), NamedServices()
    numbers = itertools.count(1)

    def store(sender: str, to: str, kind: str, wakes: bool) -> None:
        stamp = next(numbers)
        mail.writer.store(Message(
            sender=sender, to=to, type=kind, title="t", body="b", id=f"20260101T000000{stamp:06d}-{sender.replace('/', '-')}-aaaa",
            created="2026-01-01T00:00:00+00:00", wake=wakes,
        ))

    def agent(addr: str, role: str | None) -> None:
        mail.put(f"{addr}/AGENT.md", f"---\nrole: {role}\n---\nWork.\n" if role is not None else "---\ncan_hire: false\n---\nWork.\n")

    def set_budget(addr: str, runs: int) -> None:
        budgets.held[norm(addr)] = runs

    def set_state(addr: str, word: str) -> None:
        states.words[norm(addr)] = word

    def offer(addr: str, names: Sequence[str]) -> None:
        services.offered[norm(addr)] = list(names)

    tree = TextOrgTree(agents, charters, mail.reader, mail.tasks, budgets, states, services)
    return OverviewWorld(
        tree, services, agent, lambda addr, wakes: store(RUNTIME, addr, "note", wakes), lambda sender, to, wakes: store(sender, to, "task", wakes),
        set_budget, set_state, offer,
    )


def disk_world(tmp_path: Path) -> OverviewWorld:
    disk = fs_agents(tmp_path)
    return _world(fs_mailbox(tmp_path), disk.directory, disk.charters)


def memory_world(tmp_path: Path) -> OverviewWorld:
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    return _world(mail, box.agents, box.agents)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    OrgTree: [disk_world, memory_world],
}
