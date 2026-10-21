"""``AgentResolver``: the agents of a blueprint, flattened parents first and settled (tools, workspace, inputs, authority, model).

Also the readings of the ``inputs`` a blueprint names, which the resolver and the validator share."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..kernel import NAME_RE, RESERVED, JsonObject, inside
from ..settings import config_default_model
from ._protocols import AgentResolution, OrgContext, PathChecking
from ._view import AGENT_KEYS, WRITE_TOOLS, items, mapping_or_empty, needs_of, s, unknown
from .api import Agent, Issue, RoleLibrary


def input_entries(value: object, where: str, issues: list[Issue]) -> list[tuple[str, bool]]:
    """``inputs`` as (path, overlap_ok) pairs. An entry is a path or ``{path: ..., allow_overlap: true}``."""
    if value is None:
        return []
    entries = [value] if isinstance(value, (str, dict)) else value
    if not isinstance(entries, list):
        issues.append(Issue("error", where, "inputs must be a list of absolute paths (read-only sources)", "inputs"))
        return []
    out: list[tuple[str, bool]] = []
    for item in entries:
        if isinstance(item, dict) and s(item.get("path")):
            out.append((s(item["path"]), item.get("allow_overlap") is True))
        elif isinstance(item, str) and item.strip():
            out.append((item.strip(), False))
        else:
            issues.append(Issue("error", where, f"an input is an absolute path or {{path: ..., allow_overlap: true}}, not {item!r}", "inputs"))
    return out


def declared_inputs(bp: Mapping[str, object]) -> list[tuple[str, str, bool]]:
    """(where, path, overlap_ok) for every input the blueprint names: ``needs.inputs`` and each agent's ``inputs``."""
    out: list[tuple[str, str, bool]] = []

    def add(raw: object, where: str) -> None:
        out.extend((where, p, ok) for p, ok in input_entries(raw, where, []))

    add(needs_of(bp).get("inputs"), "needs.inputs")

    def walk(agents: object, prefix: str) -> None:
        for raw in agents if isinstance(agents, list) else []:
            if not isinstance(raw, dict):
                continue
            addr = f"{prefix}/{s(raw.get('name'))}" if prefix else s(raw.get("name"))
            add(raw.get("inputs"), f"agents[{addr}]")
            walk(raw.get("children"), addr)

    walk(bp.get("agents"), "")
    return out


def review_roots(agents: Sequence[Agent], project_ws: Path | None) -> list[Path]:
    """The folders the work under review lives in: the project workspace and every author's workspace."""
    roots = [project_ws] if project_ws else []
    roots += [Path(x.workspace) for x in agents if x.kind == "author" and x.workspace and any(t in x.tools for t in WRITE_TOOLS)]
    return list(dict.fromkeys(roots))


def _verifier_inputs(agents: Sequence[Agent], by: Mapping[str, Agent], project_ws: Path | None) -> None:
    """A verifier reads what it reviews: the project workspace and the authors' workspaces become read-only ``inputs``
    wherever it has no write access to them (hirearchy ``read`` accepts paths inside a caller's inputs; kiro ``read`` too
    when it holds that tool). An explicit ``inputs`` list is the blueprint's decision; ``validate`` warns when it falls
    short. Managers hold the union of their reports' inputs, so authority keeps narrowing."""
    roots = review_roots(agents, project_ws)
    for a in reversed(agents):  # reports before their manager
        explicit = "inputs" in a.raw
        if a.kind == "verifier" and not a.children and not explicit:
            parent = by.get(a.parent) if a.parent else None
            own = Path(a.workspace) if a.workspace else None
            for r in roots:
                if own and (inside(r, own) or inside(own, r)):
                    continue  # its own workspace (writable) or a folder around it: no read-only copy of that
                if parent and ("inputs" in parent.raw or "workspace" in parent.raw):
                    held = [Path(b) for b in (parent.workspace, *parent.inputs) if b]
                    if not any(inside(r, b) for b in held):
                        continue  # the manager could not hand it down; validate warns
                if str(r) not in a.inputs:
                    a.inputs.append(str(r))
        elif a.children and not explicit:
            base = Path(a.workspace) if a.workspace else None
            ins = [p for c in a.children for p in by[c].inputs]
            a.inputs = list(dict.fromkeys(p for p in ins if not (base and inside(Path(p), base))))


class AgentResolver(AgentResolution):
    def __init__(self, roles: RoleLibrary, paths: PathChecking) -> None:
        self._roles = roles
        self._paths = paths

    def _walk(self, raw_agents: object, parent: Agent | None, out: list[Agent], issues: list[Issue], where: str) -> list[str]:
        """Flatten the nested agents list into ``out`` (parents first); returns the addresses created at this level."""
        names: list[str] = []
        if not isinstance(raw_agents, list):
            issues.append(Issue("error", where, "must be a list of agents", "agents"))
            return names
        seen: set[str] = set()
        for i, raw in enumerate(raw_agents):
            if not isinstance(raw, dict):
                issues.append(Issue("error", f"{where}[{i}]", "an agent is a mapping with at least a name and a template or charter", "agents"))
                continue
            name = s(raw.get("name"))
            addr = f"{parent.addr}/{name}" if parent else name
            here = f"agents[{addr or i}]"
            if not NAME_RE.fullmatch(name) or name in RESERVED:
                issues.append(Issue("error", here, f"invalid agent name '{name}': use lowercase letters, digits and dashes (max 32, starting with a letter), not a reserved word", "name"))
                continue
            if name in seen:
                issues.append(Issue("error", here, f"duplicate name '{name}' among siblings; rename one", "name"))
                continue
            seen.add(name)
            unknown(raw, AGENT_KEYS, here, issues)
            tname = s(raw.get("template"))
            role = self._roles.get_role(tname) if tname else None
            if tname and role is None:
                issues.append(Issue("error", here, f"unknown template '{tname}'; available: {', '.join(self._roles.role_names())}", "template"))
            extra = s(raw.get("charter"))
            if not tname and not extra:
                issues.append(Issue("error", here, "give a template (e.g. 'researcher') or a charter text", "template"))
            kind = s(raw.get("kind")) or (role.kind if role else "")
            a = Agent(addr, name, parent.addr if parent else None, here, template=role, extra=extra, raw=raw)
            a.role = s(raw.get("role")) or (role.title if role else name)
            a.kind = kind
            scale = raw.get("scale")
            a.scale = scale if isinstance(scale, int) and scale >= 1 else 1
            if "scale" in raw and a.scale != scale:
                issues.append(Issue("error", here, "scale must be a whole number >= 1", "scale"))
            out.append(a)
            names.append(addr)
            if parent:
                parent.children.append(addr)
            if raw.get("children"):
                self._walk(raw["children"], a, out, issues, f"{here}.children")
        return names

    def resolve(self, bp: Mapping[str, object], org: OrgContext, roots: Sequence[Path], issues: list[Issue]) -> list[Agent]:
        needs = needs_of(bp)
        cfg = org.config()
        agents: list[Agent] = []
        self._walk(bp.get("agents"), None, agents, issues, "agents")
        by = {a.addr: a for a in agents}
        models = mapping_or_empty(needs.get("models"))
        default_model = config_default_model(cfg)  # every tier without a mapped id resolves to this

        # workspace of the whole project: used by agents that write or run commands and name no workspace
        project_ws = None
        if s(needs.get("workspace")):
            project_ws = self._paths.check(needs["workspace"], "needs.workspace", issues, org, roots, what="workspace", dir_must_exist=True)

        def check_inputs(raw: object, where: str) -> list[Path]:
            """The named inputs that pass the path checks and exist (an input is a source, so it must be there)."""
            found: list[Path] = []
            for text, _ in input_entries(raw, where, issues):
                p = self._paths.check(text, where, issues, org, roots, what="input", dir_must_exist=False)
                if p is None:
                    continue
                if not p.exists():
                    issues.append(Issue("error", where, f"input {p} does not exist; inputs are read-only sources and must be there already", "inputs"))
                elif p not in found:
                    found.append(p)
            return found

        needs_inputs = check_inputs(needs.get("inputs"), "needs.inputs")
        ws_checked: dict[str, Path | None] = {}

        def own_workspace(a: Agent) -> str | None:
            raw = a.raw.get("workspace")
            if s(raw):
                if a.addr not in ws_checked:
                    ws_checked[a.addr] = self._paths.check(raw, a.where, issues, org, roots, what="workspace", dir_must_exist=True)
                p = ws_checked[a.addr]
                return str(p) if p else None
            return None

        def settle(a: Agent) -> None:
            for c in a.children:
                settle(by[c])
            kids = [by[c] for c in a.children]
            if not a.kind:
                a.kind = "manager" if kids else "author"
            # tools: explicit, else the template's; a manager must hold what it hands to reports (authority only narrows)
            if "tools" in a.raw:
                a.tools = sorted(set(items(a.raw["tools"])))
            else:
                a.tools = sorted(set(a.template.tools if a.template else ()) | {t for k in kids for t in k.tools})
            ws = own_workspace(a)
            if ws is None and "workspace" not in a.raw:
                if kids:
                    wss = [Path(k.workspace) for k in kids if k.workspace]
                    if wss:
                        common: Path | None = Path(os.path.commonpath([str(w) for w in wss]))
                        if len(wss) > 1 and common not in wss:  # derived, so it must pass the same checks as a written one
                            common = self._paths.check(common, a.where, issues, org, roots, what="derived manager workspace (common parent of its reports')", dir_must_exist=False)
                        ws = str(common) if common else None
                elif project_ws and any(t in a.tools for t in WRITE_TOOLS):
                    ws = str(project_ws)
            a.workspace = ws
            # inputs: its own list if it names one; a manager holds what its team holds; else the project's
            if "inputs" in a.raw:
                ins = check_inputs(a.raw["inputs"], a.where)
            elif kids:
                ins = [p for k in kids for p in map(Path, k.inputs)]
            else:
                ins = list(needs_inputs)
                if ws is None and project_ws and "read" in a.tools and not any(t in a.tools for t in WRITE_TOOLS):
                    ins.append(project_ws)  # a reader of the project (e.g. a code reviewer) sees it, read-only
            base = Path(ws) if ws else None
            a.inputs = list(dict.fromkeys(str(p) for p in ins if not (base and inside(p, base))))
            a.can_hire = bool(a.raw["can_hire"]) if "can_hire" in a.raw else bool(kids)
            mc = a.raw.get("max_children", len(kids) if kids else 0)
            a.max_children = mc if isinstance(mc, int) and not isinstance(mc, bool) and mc >= 0 else -1
            if a.max_children < 0:
                issues.append(Issue("error", a.where, "max_children must be a whole number >= 0", "children"))
                a.max_children = len(kids)
            # model: explicit id or tier name, else the template's tier; a tier needs.models does not map resolves to the org default
            m = s(a.raw.get("model"))
            a.tier = a.template.tier if a.template else ""
            if m in ("cheap", "strong"):
                a.tier = m
                m = s(models.get(m))
            elif not m and a.tier:
                m = s(models.get(a.tier))
            a.model = m or default_model

        for a in agents:
            if a.parent is None:
                settle(a)
        _verifier_inputs(agents, by, project_ws)
        return agents
