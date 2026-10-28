"""The agents an extension adds (design 5.1, 5.2): read with today's ``AgentResolver``, then checked against the parent they are added under."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from ..kernel import ROOT, inside, norm
from ..settings import model_floor_problem
from ._extension_org import Reads, read_held
from ._shapes import Held, LimitChange
from ._view import WRITE_TOOLS, s
from .api import Agent, Issue

CHARTER_EXTRA_MAX = 4000
NO_PARENT = "name the agent it reports to (parent: <address>), or root for a new team."
NO_SUCH_PARENT = "{parent} is not an agent of this organization (it never was, or it was retired): add under an agent that exists, or under root for a new team."
TAKEN = "{addr} already exists{also}: pick another name (the address of a retired agent may be used again)."
TWICE = " in this change too"
TOO_DEEP = "{addr} would be at depth {d}, but the organization allows {limit}: flatten the tree, or add limits: [{{org: max_depth, value: {d}}}] to this change."
CAPACITY = (
    "{parent} may have {m} direct reports and has {k}; this change adds {a}. Add limits: [{{agent: {parent}, max_children: {n}{hire}}}] to this change "
    "(the user sees it in the plan)."
)
TOOLS = "tools {extra} are not held by {parent}; a report can only be given what its parent holds: choose tools {parent} has."
WORKSPACE = "workspace {path} is not inside {parent}'s workspace {held}; a report works inside its parent's workspace."
NO_WORKSPACE = "workspace {path} but {parent} has none; a report works inside its parent's workspace."
INPUTS = "input {path} is not inside {parent}'s inputs or workspace; a parent can only hand down what it can read."
TOO_MANY_CHILDREN = "{n} children but max_children is {m}; raise max_children."
NO_HIRING = "has children but can_hire is false; remove can_hire: false."
CHARTER_EXTRA = "charter_extra is text of 1 to " + str(CHARTER_EXTRA_MAX) + " characters, appended under 'Additional instructions'."
READS_NOTHING = "has built-in read but no workspace or inputs, so it can read nothing outside the organization; give it inputs or a workspace."
CANNOT_READ = "{addr} reviews work in {blind} but cannot read it (not in its workspace or inputs), so it would review pasted text, not the files; add the path to its inputs."
_AGENT_PATH = re.compile(r"^agents\[[^\]]*\](.*)$")


def _remapped(path: str, where: str) -> str:
    """The path of an issue of the sub-blueprint (``agents[checker].children``) as a path of the entry it came from."""
    found = _AGENT_PATH.match(path)
    return where + found.group(1) if found else f"{where} {path}"


def where_of(i: int) -> str:
    return f"extend.add_agents[{i}]"


def _full(prefix: str, addr: str) -> str:
    return addr if prefix == ROOT else f"{prefix}/{addr}"


def _readdress(agents: Sequence[Agent], parent: str, where: str) -> None:
    """The agents of a sub-blueprint (addresses from the entry down) at their places under ``parent``."""
    for a in agents:
        a.parent = parent if a.parent is None and parent != ROOT else (_full(parent, a.parent) if a.parent else None)
        a.addr = _full(parent, a.addr)
        a.children = [_full(parent, c) for c in a.children]
        a.where = where + (_AGENT_PATH.sub(r"\1", a.where) if _AGENT_PATH.match(a.where) else "")


def review_roots_under(reads: Reads, parent: str, siblings: Sequence[Agent]) -> list[Path]:
    """The workspaces a verifier under ``parent`` reviews: those of the authors among its siblings (existing or added) that can write."""
    found: list[Path] = []
    if parent != ROOT:
        for kid in reads.agents.children(parent):
            held = read_held(reads.agents, reads.charters, reads.roles, kid)
            if held.workspace and not held.verifier and not reads.agents.children(kid) and any(t in held.tools for t in WRITE_TOOLS):
                found.append(Path(held.workspace))
    found += [Path(a.workspace) for a in siblings if a.workspace and a.kind == "author" and any(t in a.tools for t in WRITE_TOOLS)]
    return list(dict.fromkeys(found))


def _verifier_inputs(reads: Reads, a: Agent, parent: Held | None, siblings: Sequence[Agent]) -> None:
    """A verifier added under ``parent`` reads what it reviews (design 5.1): the workspaces of its siblings that its parent holds become read-only inputs."""
    if a.kind != "verifier" or a.children or "inputs" in a.raw:
        return
    own = Path(a.workspace) if a.workspace else None
    for r in review_roots_under(reads, a.parent or ROOT, siblings):
        if own and (inside(r, own) or inside(own, r)):
            continue
        if parent is not None and (parent.workspace or parent.inputs):
            if not any(inside(r, Path(b)) for b in (parent.workspace, *parent.inputs) if b):
                continue
        if str(r) not in a.inputs:
            a.inputs.append(str(r))


def _narrowing(a: Agent, parent_addr: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str], issues: list[Issue]) -> None:
    extra = sorted(set(a.tools) - set(tools))
    if extra:
        issues.append(Issue("error", a.where, TOOLS.format(extra=", ".join(extra), parent=parent_addr), "extend-tools"))
    if a.workspace:
        if not workspace:
            issues.append(Issue("error", a.where, NO_WORKSPACE.format(path=a.workspace, parent=parent_addr), "extend-workspace"))
        elif not inside(Path(a.workspace), Path(workspace)):
            issues.append(Issue("error", a.where, WORKSPACE.format(path=a.workspace, parent=parent_addr, held=workspace), "extend-workspace"))
    bases = [Path(b) for b in (workspace, *inputs) if b]
    for path in a.inputs:
        if not any(inside(Path(path), b) for b in bases):
            issues.append(Issue("error", a.where, INPUTS.format(path=path, parent=parent_addr), "extend-inputs"))


def added_agents(
    reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], limits: Mapping[str, LimitChange], max_depth: int, cfg: Mapping[str, object],
    allowed_roots: Sequence[str | Path] | None, issues: list[Issue],
) -> tuple[list[Agent], dict[str, str]]:
    """The agents of the ``add_agents`` entries, parents first, and their ``charter_extra`` by address; the problems go to ``issues``."""
    agents: list[Agent] = []
    extras: dict[str, str] = {}
    held: dict[str, Held] = {}
    adds: dict[str, int] = {}
    taken: set[str] = set()
    for i, entry in entries:
        where = where_of(i)
        if not s(entry.get("parent")):
            issues.append(Issue("error", where, NO_PARENT, "extend-parent"))
            continue
        parent = norm(s(entry.get("parent")))
        if parent != ROOT and not reads.agents.exists(parent):
            issues.append(Issue("error", where, NO_SUCH_PARENT.format(parent=parent), "extend-parent"))
            continue
        if parent != ROOT and parent not in held:
            held[parent] = read_held(reads.agents, reads.charters, reads.roles, parent)
        extra = entry.get("charter_extra")
        if extra is not None and (not isinstance(extra, str) or not 1 <= len(extra.strip()) <= CHARTER_EXTRA_MAX):
            issues.append(Issue("error", where, CHARTER_EXTRA, "extend-form"))
        mine = {k: v for k, v in entry.items() if k not in ("parent", "charter_extra")}
        above = held.get(parent)
        roots = [*reads.roots.roots(allowed_roots), *(Path(b) for b in ((above.workspace, *above.inputs) if above else ()) if b)]
        needs: dict[str, object] = {"inputs": list(above.inputs)} if above and above.inputs else {}
        made: list[Issue] = []
        found = reads.resolver.resolve({"needs": needs, "agents": [mine]}, reads.org, roots, made)
        issues += [replace(i2, path=_remapped(i2.path, where)) for i2 in made]
        if not found:
            continue
        _readdress(found, parent, where)
        top = found[0]
        for a in found:
            if reads.agents.exists(a.addr) or a.addr in taken:
                issues.append(Issue("error", a.where, TAKEN.format(addr=a.addr, also=TWICE if a.addr in taken else ""), "extend-name"))
            taken.add(a.addr)
            if a.depth > max_depth:
                issues.append(Issue("error", a.where, TOO_DEEP.format(addr=a.addr, d=a.depth, limit=max_depth), "extend-depth"))
            if problem := model_floor_problem(cfg, a.model):
                issues.append(Issue("error", a.where, problem, "model-floor"))
            if len(a.children) > a.max_children:
                issues.append(Issue("error", a.where, TOO_MANY_CHILDREN.format(n=len(a.children), m=a.max_children), "extend-capacity"))
            if a.children and "can_hire" in a.raw and not a.raw["can_hire"]:
                issues.append(Issue("error", a.where, NO_HIRING, "extend-capacity"))
        siblings = [a for a in agents if a.parent == top.parent] + [top]
        _verifier_inputs(reads, top, above, siblings)
        by = {a.addr: a for a in found}
        for a in found:
            p = by.get(a.parent) if a.parent else None
            if p is not None:
                _narrowing(a, p.addr, p.tools, p.workspace, p.inputs, issues)
            elif above is not None:
                _narrowing(a, above.addr, above.tools, above.workspace, above.inputs, issues)
            if "read" in a.tools and not a.workspace and not a.inputs:
                issues.append(Issue("warning", a.where, READS_NOTHING, "read-nothing"))
        if top.kind == "verifier" and not top.children:
            work = review_roots_under(reads, top.parent or ROOT, siblings)
            held_paths = [Path(b) for b in (top.workspace, *top.inputs) if b]
            blind = [r for r in work if not any(inside(r, b) for b in held_paths)]
            if blind:
                issues.append(Issue("warning", top.where, CANNOT_READ.format(addr=top.addr, blind=", ".join(map(str, blind))), "verifier-cannot-read"))
        if extra and isinstance(extra, str):
            extras[top.addr] = extra.strip()
        adds[parent] = adds.get(parent, 0) + 1
        agents += found
    for parent, n in adds.items():
        h = held.get(parent)
        if h is None:
            continue
        change = limits.get(parent)
        can_hire = h.can_hire if change is None or change.can_hire is None else change.can_hire
        m = h.max_children if change is None or change.max_children is None else change.max_children
        if not can_hire or h.reports + n > m:
            where = next(where_of(i) for i, e in entries if s(e.get("parent")) and norm(s(e.get("parent"))) == parent)
            issues.append(Issue("error", where, CAPACITY.format(
                parent=parent, m=m if can_hire else 0, k=h.reports, a=n, n=h.reports + n, hire="" if can_hire else ", can_hire: true",
            ), "extend-capacity"))
    return agents, extras
