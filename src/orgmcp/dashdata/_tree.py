"""The agent tree of a snapshot: who is below whom, what runs and waits below a node, and the order the tree is shown in."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import ROOT, parent
from ._data import AgentRow


def arrange(rows: dict[str, AgentRow], agents: Sequence[str]) -> list[str]:
    """Fill ``children`` and the roll-ups of the rows (``agents``: every agent, parents before children) and return the order: root first,
    then depth-first."""
    for a in agents:  # children lists from the addresses (one listing, no second directory walk)
        up = parent(a) or ROOT
        if up in rows and a not in rows[up].children:
            rows[up].children.append(a)
    for a in reversed(agents):  # roll running / queued up to the ancestors (shown when a node is collapsed)
        r = rows[a]
        p = rows.get(r.parent or ROOT)
        if p is not None and p.addr != a:
            p.below_running += r.below_running + (r.kind == "running")
            p.below_queued += r.below_queued + (r.kind == "queued")
    order = [ROOT]
    stack = list(reversed(rows[ROOT].children))
    while stack:
        a = stack.pop()
        if a in rows:
            order.append(a)
            stack.extend(reversed(rows[a].children))
    return order
