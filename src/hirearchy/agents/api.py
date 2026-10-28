"""The public surface of ``agents``: the on-disk registry of agents, their charters and their memory.

``AgentDirectory`` answers who exists and where they sit in the tree, ``CharterReader`` reads an agent's charter and memory,
``AgentRegistry`` is the only writer of ``AGENT.md``, of the directory skeleton of an agent and of ``.retired/``, and
``RetiredArchive`` reads the trees that were retired (their record, and the memory and the results of each agent in them).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, Message

__all__ = [
    "AgentDirectory",
    "AgentRegistry",
    "CharterReader",
    "RetiredArchive",
    "RetiredTree",
]


@runtime_checkable
class AgentDirectory(Protocol):
    def exists(self, addr: str) -> bool:
        """``root`` is always true; any other address needs valid, unreserved name parts and ``<addr>/AGENT.md`` as a file."""
        ...

    def require(self, addr: str) -> str:
        """The normalized address, or ``OrgError("no such agent: <addr>")``."""
        ...

    def children(self, addr: str) -> list[str]:
        """The direct reports, sorted: directories with a valid, unreserved name and an ``AGENT.md``."""
        ...

    def agents(self) -> list[str]:
        """Every agent except root, parents before children (siblings sorted)."""
        ...

    def subtree(self, addr: str) -> list[str]:
        """``addr`` and everything below it (``addr`` first, every agent before its descendants), whether or not ``addr`` exists."""
        ...


@runtime_checkable
class CharterReader(Protocol):
    def charter(self, addr: str) -> tuple[JsonObject, str]:
        """``(frontmatter, body stripped)`` of ``<addr>/AGENT.md``; root has a fixed charter; a missing file is ``FileNotFoundError``."""
        ...

    def memory(self, addr: str) -> str:
        """``<addr>/MEMORY.md`` exactly as written, or ``""`` when there is none."""
        ...


@runtime_checkable
class AgentRegistry(Protocol):
    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        """The directory skeleton (``inbox inflight read sent work runs``), an empty ``MEMORY.md``, then ``AGENT.md``
        (``meta`` as frontmatter in its order, ``charter_text`` as the body). ``AGENT.md`` comes last: until it is there the directory is no agent."""
        ...

    def rewrite_charter(self, addr: str, text: str) -> None:
        """Replace ``AGENT.md`` by ``text`` as it is (the callers did all the authority checks)."""
        ...

    def archive(self, addr: str, stamp: str, record: Mapping[str, str] | None = None) -> str:
        """Move the agent's directory, with everything below it, to ``.retired/<addr with . for />-<stamp>``; returns that name. With ``record``
        (``retired``, ``by``, ``reason`` and, when the approval is known, ``approved_in``) the moved tree's top directory then gets a ``RETIRED.md``
        with it as its frontmatter. The record is written after the move: an ``OSError`` from that write leaves the tree retired."""
        ...


_STAMP_SUFFIX = re.compile(r"-\d{8}T\d{6}$")  # the ``%Y%m%dT%H%M%S`` stamp ``AgentRegistry.archive`` appends to the name of a retired tree


@dataclass(frozen=True)
class RetiredTree:
    name: str  # the directory name in ``.retired``: ``<address with . for />-<stamp>``
    top_level: bool  # the retired agent was a direct report of root
    path: Path  # the directory

    @property
    def addr(self) -> str:
        """The address of the retired agent: ``name`` without its ``-<stamp>`` suffix, ``.`` read as ``/`` (a name without a stamp is its own address)."""
        return _STAMP_SUFFIX.sub("", self.name).replace(".", "/")


@runtime_checkable
class RetiredArchive(Protocol):
    def trees(self) -> list[RetiredTree]:
        """Every retired tree, sorted by name; ``top_level`` is read from the name (no dot before the ``-<stamp>`` suffix)."""
        ...

    def run_count(self) -> int:
        """The run logs (``*.log``, not hidden) inside the ``runs/`` directories of all retired trees."""
        ...

    def unspent_budget(self, tree: RetiredTree) -> int:
        """What the tree still held when it was retired: for every agent directory in it, received (inbox, inflight, read)
        minus sent minus run logs, in runs of budget."""
        ...

    def credited(self) -> int:
        """The runs the runtime gave back with run credits (``kernel.is_run_credit``) that sit in the received boxes (inbox, inflight, read)
        of every agent directory of all retired trees: budget the retired agents received, besides what root and their parents handed down."""
        ...

    def record(self, tree: RetiredTree) -> Mapping[str, str]:
        """The frontmatter of the tree's ``RETIRED.md`` (``retired``, ``by``, ``reason``, ``approved_in``), every value as text; ``{}`` when the
        tree has no record (a tree retired before Phase 2) or it cannot be read."""
        ...

    def memory(self, tree: RetiredTree, addr: str) -> str:
        """The archived ``MEMORY.md`` of agent ``addr`` of the tree (the tree's top agent, ``tree.addr``, or an agent below it); ``""`` when the agent
        or its file is not there. ``OSError`` when the file cannot be read."""
        ...

    def results(self, tree: RetiredTree, addr: str) -> list[Message]:
        """The result messages in the archived ``sent/`` of agent ``addr`` of the tree, oldest first; ``[]`` when there are none. ``OSError`` when a
        file cannot be read."""
        ...
