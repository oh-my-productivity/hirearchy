"""The public surface of ``overview``: the text ``status`` shows of the whole organization.

One line for root (what waits for the human) and one line per agent, below its parent and indented by its depth: its role, its state, its budget,
how many tasks it has open, has delegated and has unread, and the services it offers. Everything on the lines is read from the other features'
ports at the moment of the call; nothing is stored.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = [
    "OrgTree",
]


@runtime_checkable
class OrgTree(Protocol):
    def tree(self) -> str:
        """``root (human): unread N, delegated N`` and then, for every agent (parents before children, siblings sorted), one line indented by two
        spaces per level: ``<name> [<role>] <state>  budget=<runs> open=<N> delegated=<N> unread=<N>``, followed by ``services: a, b`` (by name)
        when the agent offers any. No trailing newline."""
        ...
