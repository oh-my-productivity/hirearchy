"""The changes an extension makes to what exists (design 5.1, 5.2): hiring limits, the organization's depth, and agents retired."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..kernel import ROOT, norm
from ._extension_org import Reads, as_int, deepest, read_held
from ._shapes import DepthChange, LimitChange, Retiring
from ._view import s
from .api import Issue

REASON_MAX = 300
LIMIT_NOT_AN_AGENT = "{agent} is not an agent of this organization: limits change an agent that exists."
LIMIT_ROOT = "root has no hiring limits to change."
LIMIT_TWICE = "{agent} has two limits entries in this change: give it one."
LIMIT_EMPTY = "give can_hire, max_children or both: this entry changes nothing."
LIMIT_CAN_HIRE = "can_hire is true or false."
LIMIT_MAX_CHILDREN = "max_children is a whole number >= 0; {agent} has {k} direct reports now, so at least {k}."
LIMIT_SAME = "{agent} already has these limits (may hire: {hire}, up to {m} direct reports): this entry changes nothing."
LIMIT_HIRES = "{agent} has {k} direct reports, so it must keep can_hire: true."
DEPTH_VALUE = "value is a whole number >= 1, and at least {deepest}, the depth of the deepest agent there is."
DEPTH_TWICE = "the organization's depth appears twice in this change: give it one entry."
DEPTH_SAME = "max_depth is already {value}: this entry changes nothing."
RETIRE_NOT_AN_AGENT = "{agent} is not an agent of this organization: retire an agent that exists."
RETIRE_ROOT = "root cannot be retired."
RETIRE_REASON = "say why in reason (1 to " + str(REASON_MAX) + " characters)."
RETIRE_NAMED = "{agent} cannot be retired in the change that names it, or something below it, in {path}: retire it in a later change."
RETIRE_TWICE = "{agent} is retired twice in this change (or inside the team of another entry): retire it once."
RETIRE_NOTHING = "{agent} is retired, and so is {other} below it: retire the team once."


def limits_of(reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], issues: list[Issue]) -> tuple[list[LimitChange], DepthChange | None]:
    """The ``limits`` entries read against the organization: the hiring limits of agents that exist, and the depth."""
    changes: list[LimitChange] = []
    depth: DepthChange | None = None
    for i, entry in entries:
        where = f"extend.limits[{i}]"
        if "org" in entry:  # the form rules left only max_depth
            value = entry.get("value")
            floor = deepest(reads.agents)
            if not isinstance(value, int) or isinstance(value, bool) or value < max(1, floor):
                issues.append(Issue("error", where, DEPTH_VALUE.format(deepest=floor), "extend-limit"))
            elif depth is not None:
                issues.append(Issue("error", where, DEPTH_TWICE, "extend-limit"))
            else:
                was = as_int(reads.org.config().get("max_depth"), 4)
                if value == was:
                    issues.append(Issue("error", where, DEPTH_SAME.format(value=value), "extend-limit"))
                else:
                    depth = DepthChange(value, was)
            continue
        agent = norm(s(entry.get("agent")))
        if agent == ROOT:
            issues.append(Issue("error", where, LIMIT_ROOT, "extend-limit"))
            continue
        if not agent or not reads.agents.exists(agent):
            issues.append(Issue("error", where, LIMIT_NOT_AN_AGENT.format(agent=agent or "(none)"), "extend-limit"))
            continue
        if any(c.agent == agent for c in changes):
            issues.append(Issue("error", where, LIMIT_TWICE.format(agent=agent), "extend-limit"))
            continue
        held = read_held(reads.agents, reads.charters, reads.roles, agent)
        can_hire, max_children = entry.get("can_hire"), entry.get("max_children")
        if can_hire is None and max_children is None:
            issues.append(Issue("error", where, LIMIT_EMPTY, "extend-limit"))
            continue
        if can_hire is not None and not isinstance(can_hire, bool):
            issues.append(Issue("error", where, LIMIT_CAN_HIRE, "extend-limit"))
            continue
        if max_children is not None and (not isinstance(max_children, int) or isinstance(max_children, bool) or max_children < held.reports):
            issues.append(Issue("error", where, LIMIT_MAX_CHILDREN.format(agent=agent, k=held.reports), "extend-limit"))
            continue
        if can_hire is False and held.reports:
            issues.append(Issue("error", where, LIMIT_HIRES.format(agent=agent, k=held.reports), "extend-limit"))
            continue
        if (can_hire is None or can_hire == held.can_hire) and (max_children is None or max_children == held.max_children):
            issues.append(Issue("error", where, LIMIT_SAME.format(agent=agent, hire="yes" if held.can_hire else "no", m=held.max_children), "extend-limit"))
            continue
        changes.append(LimitChange(agent, can_hire, max_children, held.can_hire, held.max_children))
    return changes, depth


def retires_of(
    reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], named: Mapping[str, str], issues: list[Issue],
) -> list[Retiring]:
    """The ``retire`` entries read against the organization. ``named`` maps every address another entry names (a parent, an owner, an agent) to the
    path of that entry: an agent is not retired in the change that names it or something below it."""
    found: list[Retiring] = []
    for i, entry in entries:
        where = f"extend.retire[{i}]"
        agent = norm(s(entry.get("agent")))
        reason = s(entry.get("reason"))
        if agent == ROOT:
            issues.append(Issue("error", where, RETIRE_ROOT, "extend-retire"))
        elif not agent or not reads.agents.exists(agent):
            issues.append(Issue("error", where, RETIRE_NOT_AN_AGENT.format(agent=agent or "(none)"), "extend-retire"))
        elif not 1 <= len(reason) <= REASON_MAX:
            issues.append(Issue("error", where, RETIRE_REASON, "extend-retire"))
        else:
            team = tuple(reads.agents.subtree(agent))
            if any(r.agent == agent for r in found) or any(agent in r.team for r in found):
                issues.append(Issue("error", where, RETIRE_TWICE.format(agent=agent), "extend-retire"))
                continue
            if (inner := next((r for r in found if r.agent in team), None)) is not None:
                issues.append(Issue("error", where, RETIRE_NOTHING.format(agent=agent, other=inner.agent), "extend-retire"))
                continue
            clash = next((path for addr, path in named.items() if addr in team), None)
            if clash is not None:
                issues.append(Issue("error", where, RETIRE_NAMED.format(agent=agent, path=clash), "extend-retire"))
                continue
            found.append(Retiring(agent, reason, team))
    return found
