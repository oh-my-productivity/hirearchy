"""Blueprints: a whole organization for one goal as a reviewable document.

A blueprint is a plain dict (YAML or JSON)::

    mission: one paragraph
    needs:                      # the elicited requirements, in the user's terms
      scope: ...
      deliverable: {description, format, max_words, path}
      quality_bar: ...  sources: ...  workspace: /abs/path  budget_runs: 25
      inputs: [/abs/read-only/folder]   # read-only sources for the agents (kiro enforces: they cannot write there)
      models: {cheap: <model id>, strong: <model id>}   model_policy: ...
      review: true|false|text   approval: ...   progress: ...
      kind: research|writing|code    code: {tests, packaging, commits}
    agents:                     # exactly one top-level agent (budget flows down from it)
      - {name, role, template, charter, model, tools, workspace, inputs, can_hire, max_children, scale, children: [...]}
    task: {to, title, goal, acceptance: [exact, checkable items], inputs: [...], budget}

``validate`` encodes what went wrong in the usability studies as checks (errors block ``apply``, warnings are
shown in the plan), ``render_plan`` produces the text the user approves, ``apply`` builds the organization.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .core import DEFAULT_CONFIG, NAME_RE, RESERVED, ROOT, Org, OrgError, split_frontmatter

ROLES_DIR = Path(__file__).parent / "roles"
WEB_TOOLS = ("web_search", "web_fetch")
WRITE_TOOLS = ("write", "shell")
SLACK = 1.25  # planned budget = estimate * SLACK when the task names no budget
TIGHT = 1.10  # a budget under estimate * TIGHT is flagged as having no slack
REWORK_RUNS = {"manager": 2, "author": 1, "verifier": 1}  # one rework cycle, see ``estimate``
KINDS = ("manager", "author", "verifier")


class BlueprintError(OrgError):
    pass


# ------------------------------------------------------------------------------------------------ issues


@dataclass(frozen=True)
class Issue:
    level: str  # "error" blocks apply; "warning" is shown in the plan
    path: str  # where in the blueprint, e.g. "needs.deliverable" or "agents[ceo/writer]"
    message: str  # what is wrong and how to fix it
    code: str = ""  # stable short name of the rule

    def render(self) -> str:
        return f"{self.level}: {self.path}: {self.message}"


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]


# ------------------------------------------------------------------------------------------- role library


@dataclass(frozen=True)
class Role:
    name: str
    title: str
    kind: str  # manager | author | verifier
    tier: str  # cheap | strong: the model tier the role needs
    tools: tuple[str, ...]
    base_runs: int  # runs for one pass of the work (managers: see ``estimate``)
    summary: str
    body: str


def role_names() -> list[str]:
    return sorted(p.stem for p in ROLES_DIR.glob("*.md"))


def get_role(name: str) -> Role | None:
    p = ROLES_DIR / f"{name}.md"
    if not NAME_RE.fullmatch(name) or not p.is_file():
        return None
    meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
    return Role(
        name, str(meta["title"]), str(meta["kind"]), str(meta.get("tier", "cheap")), tuple(meta.get("tools") or ()),
        int(meta.get("base_runs", 2)), str(meta.get("summary", "")), body.strip(),
    )


# ------------------------------------------------------------------------------------------------ loading


def load(source) -> dict:
    """A blueprint from a path (``Path`` or an existing file name) or from YAML/JSON text."""
    if isinstance(source, dict):
        bp = source
    else:
        text = None
        if isinstance(source, Path):
            text = source.expanduser().read_text(encoding="utf-8")
        elif isinstance(source, str) and "\n" not in source and len(source) < 1024:
            p = Path(source).expanduser()
            if p.is_file():
                text = p.read_text(encoding="utf-8")
        if text is None:
            text = str(source)
        bp = _parse(text)
    return _normalize(bp)


def load_text(text: str) -> dict:
    """A blueprint from YAML/JSON text only. Never reads a file, whatever the text looks like (for text from a tool call)."""
    return _normalize(_parse(text))


def _parse(text: str):
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BlueprintError(f"blueprint is not valid YAML/JSON: {exc}") from exc


def _normalize(bp) -> dict:
    if not isinstance(bp, dict):
        raise BlueprintError("a blueprint is a mapping with mission, needs, agents and task")
    task = bp.get("task")
    if isinstance(task, dict):  # lenient: acceptance as a bullet/numbered text becomes a list
        acc = task.get("acceptance")
        if isinstance(acc, str):
            lines = [re.sub(r"^\s*(?:[-*+]|\d{1,2}[.)])\s+", "", ln).strip() for ln in acc.splitlines()]
            task = {**task, "acceptance": [ln for ln in lines if ln]}
            bp = {**bp, "task": task}
    return bp


# --------------------------------------------------------------------------------------- resolved agents


@dataclass
class Agent:
    addr: str
    name: str
    parent: str | None  # address of the parent; None for the top-level agent
    where: str  # issue path
    role: str = ""
    template: Role | None = None
    kind: str = "author"
    extra: str = ""  # charter text from the blueprint (appended to the template, or the whole charter)
    model: str | None = None  # resolved model id (None = org default)
    tier: str = ""
    tools: list[str] = field(default_factory=list)
    workspace: str | None = None
    inputs: list[str] = field(default_factory=list)  # read-only paths (absolute), see ``_input_entries``
    can_hire: bool = False
    max_children: int = 5
    scale: int = 1
    children: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def depth(self) -> int:
        return self.addr.count("/") + 1


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t for t in re.split(r"[,\s]+", value) if t]
    return [str(v).strip() for v in value if str(v).strip()]


def _unknown(d: dict, known: set[str], where: str, issues: list[Issue]) -> None:
    for k in d:
        if k not in known:
            issues.append(Issue("warning", where, f"unknown key '{k}' is ignored; check the spelling (known: {', '.join(sorted(known))})", "unknown-key"))


NEEDS_KEYS = {"scope", "deliverable", "quality_bar", "sources", "workspace", "inputs", "budget_runs", "models",
              "model_policy", "review", "approval", "progress", "kind", "code"}
AGENT_KEYS = {"name", "role", "template", "charter", "model", "tools", "workspace", "inputs", "can_hire", "max_children",
              "children", "scale", "kind"}


def _needs(bp: dict) -> dict:
    n = bp.get("needs")
    return n if isinstance(n, dict) else {}


def _deliverable(bp: dict) -> dict:
    d = _needs(bp).get("deliverable")
    if isinstance(d, str):
        return {"description": d}
    return d if isinstance(d, dict) else {}


def _criteria(bp: dict) -> list[str]:
    t = bp.get("task")
    acc = t.get("acceptance") if isinstance(t, dict) else None
    return [_s(c) for c in acc] if isinstance(acc, list) else []


def _cfg(org: Org | None) -> dict:
    return org.config if org is not None else dict(DEFAULT_CONFIG)


def _walk(raw_agents, parent: Agent | None, out: list[Agent], issues: list[Issue], where: str, org: Org | None) -> list[str]:
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
        name = _s(raw.get("name"))
        addr = f"{parent.addr}/{name}" if parent else name
        here = f"agents[{addr or i}]"
        if not NAME_RE.fullmatch(name) or name in RESERVED:
            issues.append(Issue("error", here, f"invalid agent name '{name}': use lowercase letters, digits and dashes (max 32, starting with a letter), not a reserved word", "name"))
            continue
        if name in seen:
            issues.append(Issue("error", here, f"duplicate name '{name}' among siblings; rename one", "name"))
            continue
        seen.add(name)
        _unknown(raw, AGENT_KEYS, here, issues)
        tname = _s(raw.get("template"))
        role = get_role(tname) if tname else None
        if tname and role is None:
            issues.append(Issue("error", here, f"unknown template '{tname}'; available: {', '.join(role_names())}", "template"))
        extra = _s(raw.get("charter"))
        if not tname and not extra:
            issues.append(Issue("error", here, "give a template (e.g. 'researcher') or a charter text", "template"))
        kind = _s(raw.get("kind")) or (role.kind if role else "")
        a = Agent(addr, name, parent.addr if parent else None, here, template=role, extra=extra, raw=raw)
        a.role = _s(raw.get("role")) or (role.title if role else name)
        a.kind = kind
        a.scale = raw["scale"] if isinstance(raw.get("scale"), int) and raw["scale"] >= 1 else 1
        if "scale" in raw and a.scale != raw["scale"]:
            issues.append(Issue("error", here, "scale must be a whole number >= 1", "scale"))
        out.append(a)
        names.append(addr)
        if parent:
            parent.children.append(addr)
        if raw.get("children"):
            _walk(raw["children"], a, out, issues, f"{here}.children", org)
    return names


def _within(p: Path, base: Path) -> bool:
    return p == base or base in p.parents


def _default_roots() -> list[Path]:
    env = os.environ.get("ORGMCP_WORKSPACE_ROOTS")
    if env:
        return [Path(r).expanduser().resolve() for r in env.split(os.pathsep) if r]
    cands = [Path.home(), Path(tempfile.gettempdir()), Path("/tmp"), Path.cwd()]
    return list(dict.fromkeys(c.resolve() for c in cands))


def _check_path(raw, where: str, issues: list[Issue], org: Org | None, roots: list[Path], *, what: str,
                dir_must_exist: bool) -> Path | None:
    """Resolve a user path and check it is absolute, inside an allowed root and away from the org and ~/.kiro."""
    text = _s(raw)
    p = Path(os.path.expanduser(text))
    if not p.is_absolute():
        issues.append(Issue("error", where, f"{what} '{text}' must be an absolute path; give the full path", "path"))
        return None
    p = p.resolve()
    if p.parent == p or not any(_within(p, r) and p != r for r in roots):
        shown = ", ".join(str(r) for r in roots)
        issues.append(Issue("error", where, f"{what} {p} is outside the allowed roots ({shown}) or is a root itself; choose a project directory inside one (extend with --allow-root or $ORGMCP_WORKSPACE_ROOTS)", "path-root"))
        return None
    if _within(p, (Path.home() / ".kiro").resolve()):
        issues.append(Issue("error", where, f"{what} {p} is inside ~/.kiro (agent configuration); choose another directory", "path-root"))
        return None
    if org is not None and (_within(p, org.root) or _within(org.root, p)):
        issues.append(Issue("error", where, f"{what} {p} overlaps the organization directory {org.root}; agents must work in a separate directory", "path-root"))
        return None
    if dir_must_exist:
        if p.exists() and not p.is_dir():
            issues.append(Issue("error", where, f"{what} {p} exists but is not a directory", "workspace"))
            return None
        if not p.exists():
            if p.parent.is_dir():
                issues.append(Issue("warning", where, f"{p} does not exist yet; apply will create it", "workspace-new"))
            else:
                issues.append(Issue("error", where, f"{p} does not exist and neither does its parent; create it or fix the path", "workspace"))
                return None
    return p


def _input_entries(value, where: str, issues: list[Issue]) -> list[tuple[str, bool]]:
    """``inputs`` as (path, overlap_ok) pairs. An entry is a path or ``{path: ..., allow_overlap: true}``."""
    if value is None:
        return []
    items = [value] if isinstance(value, (str, dict)) else value
    if not isinstance(items, list):
        issues.append(Issue("error", where, "inputs must be a list of absolute paths (read-only sources)", "inputs"))
        return []
    out: list[tuple[str, bool]] = []
    for item in items:
        if isinstance(item, dict) and _s(item.get("path")):
            out.append((_s(item["path"]), item.get("allow_overlap") is True))
        elif isinstance(item, str) and item.strip():
            out.append((item.strip(), False))
        else:
            issues.append(Issue("error", where, f"an input is an absolute path or {{path: ..., allow_overlap: true}}, not {item!r}", "inputs"))
    return out


def declared_inputs(bp: dict) -> list[tuple[str, str, bool]]:
    """(where, path, overlap_ok) for every input the blueprint names: ``needs.inputs`` and each agent's ``inputs``."""
    out: list[tuple[str, str, bool]] = []

    def add(raw, where: str) -> None:
        out.extend((where, p, ok) for p, ok in _input_entries(raw, where, []))

    add(_needs(bp).get("inputs"), "needs.inputs")

    def walk(agents, prefix: str) -> None:
        for raw in agents if isinstance(agents, list) else []:
            if not isinstance(raw, dict):
                continue
            addr = f"{prefix}/{_s(raw.get('name'))}" if prefix else _s(raw.get("name"))
            add(raw.get("inputs"), f"agents[{addr}]")
            walk(raw.get("children"), addr)

    walk(bp.get("agents"), "")
    return out


def _resolve(bp: dict, org: Org | None, roots: list[Path], issues: list[Issue]) -> list[Agent]:
    needs = _needs(bp)
    cfg = _cfg(org)
    agents: list[Agent] = []
    _walk(bp.get("agents"), None, agents, issues, "agents", org)
    by = {a.addr: a for a in agents}
    models = needs.get("models") if isinstance(needs.get("models"), dict) else {}
    default_model = cfg.get("default_model")

    # workspace of the whole project: used by agents that write or run commands and name no workspace
    project_ws = None
    if _s(needs.get("workspace")):
        project_ws = _check_path(needs["workspace"], "needs.workspace", issues, org, roots, what="workspace", dir_must_exist=True)

    def check_inputs(raw, where: str) -> list[Path]:
        """The named inputs that pass the path checks and exist (an input is a source, so it must be there)."""
        found: list[Path] = []
        for text, _ in _input_entries(raw, where, issues):
            p = _check_path(text, where, issues, org, roots, what="input", dir_must_exist=False)
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
        if _s(raw):
            if a.addr not in ws_checked:
                ws_checked[a.addr] = _check_path(raw, a.where, issues, org, roots, what="workspace", dir_must_exist=True)
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
            a.tools = sorted(set(_list(a.raw["tools"])))
        else:
            a.tools = sorted(set(a.template.tools if a.template else ()) | {t for k in kids for t in k.tools})
        ws = own_workspace(a)
        if ws is None and "workspace" not in a.raw:
            if kids:
                wss = [Path(k.workspace) for k in kids if k.workspace]
                if wss:
                    common = Path(os.path.commonpath([str(w) for w in wss]))
                    if len(wss) > 1 and common not in wss:  # derived, so it must pass the same checks as a written one
                        common = _check_path(common, a.where, issues, org, roots, what="derived manager workspace (common parent of its reports')", dir_must_exist=False)
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
        a.inputs = list(dict.fromkeys(str(p) for p in ins if not (base and _within(p, base))))
        a.can_hire = bool(a.raw["can_hire"]) if "can_hire" in a.raw else bool(kids)
        mc = a.raw.get("max_children", len(kids) if kids else 0)
        a.max_children = mc if isinstance(mc, int) and not isinstance(mc, bool) and mc >= 0 else -1
        if a.max_children < 0:
            issues.append(Issue("error", a.where, "max_children must be a whole number >= 0", "children"))
            a.max_children = len(kids)
        # model: explicit id or tier name, else the template's tier if the blueprint maps tiers, else the org default
        m = _s(a.raw.get("model"))
        a.tier = a.template.tier if a.template else ""
        if m in ("cheap", "strong"):
            a.tier = m
            m = _s(models.get(m))
            if not m:
                issues.append(Issue("error", a.where, f"model '{a.tier}' is a tier but needs.models.{a.tier} is not set; add needs.models: {{cheap: <id>, strong: <id>}}", "model-tier"))
        elif not m and a.tier and _s(models.get(a.tier)):
            m = _s(models[a.tier])
        a.model = m or (_s(default_model) or None)

    for a in agents:
        if a.parent is None:
            settle(a)
    return agents


# ------------------------------------------------------------------------------------------- estimate


def estimate(agents: list[Agent]) -> dict:
    """Runs one pass plus one rework cycle needs. The model behind the budget check and the budget split.

    Per agent, one *pass* of the work and one *rework* cycle (one review finds problems, the author fixes them):

    * worker (author or verifier): ``pass = template.base_runs * scale`` (researcher 3, writer 2, engineer 4,
      fact-checker 2, reviewer 1, tester 2, code-reviewer 2; a custom charter counts 2). ``rework = 1``
      (an author fixes its file; a verifier re-checks).
    * manager: ``pass = 1 (plan and delegate) + 1 per direct report (process its result) + 1 (final check and report)``;
      ``rework = 2`` (send the findings back, process the revised result).

    ``total`` is the sum over all agents of pass + rework: the minimum budget for a pipeline with one review and one rework cycle.
    The planned budget is ``ceil(total * 1.25)`` unless the task names one; below ``total * 1.1`` is flagged as having no slack.
    """
    per: dict[str, dict] = {}
    for a in agents:
        if a.kind == "manager" or a.children:
            p, r = 2 + len(a.children), REWORK_RUNS["manager"]
        else:
            p = (a.template.base_runs if a.template else 2) * a.scale
            r = REWORK_RUNS.get(a.kind, 1)
        per[a.addr] = {"pass": p, "rework": r, "total": p + r}
    return {"per": per, "total": sum(v["total"] for v in per.values())}


def planned_total(bp: dict, est_total: int) -> int:
    t = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    if isinstance(t.get("budget"), int) and not isinstance(t.get("budget"), bool):
        return t["budget"]
    cap = _needs(bp).get("budget_runs")
    plan = math.ceil(est_total * SLACK)
    return min(plan, cap) if isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1 else plan


def budget_split(agents: list[Agent], total: int) -> dict[str, dict]:
    """addr -> {grant, keeps}: what the parent hands down at first, and what the agent keeps for itself.

    A worker is granted its pass runs (its rework run is kept by its manager); a manager child is granted its whole
    subtree (pass and rework) so it can run its own review loop. The top agent receives ``total``.
    """
    est = estimate(agents)["per"]
    by = {a.addr: a for a in agents}

    def sub(addr: str, key: str) -> int:
        return est[addr][key] + sum(sub(c, key) for c in by[addr].children)

    out: dict[str, dict] = {}

    def fill(addr: str, budget: int) -> None:
        a = by[addr]
        grants = {c: (sub(c, "pass") + (sub(c, "total") - sub(c, "pass") if by[c].children else 0)) for c in a.children}
        out[addr] = {"grant": budget, "keeps": budget - sum(grants.values())}
        for c in a.children:
            fill(c, grants[c])

    for a in agents:
        if a.parent is None:
            fill(a.addr, total)
    return out


# --------------------------------------------------------------------------------------- text heuristics

_WEB_STRONG = re.compile(r"https?://|\bweb\s*(?:search\w*|fetch\w*|access|sources?|sites?|pages?|research\w*|brows\w+)|\bwebsites?\b|\burls?\b|\binternet\b|\bonline\b|\bcit(?:e|es|ed|ation|ations)\b|\bbrowse\w*", re.I)
_WEB_WEAK = re.compile(r"\b(?:current|latest|up-to-date|recent|as of|pricing|prices?|releases?|licen[sc]es?)\b", re.I)
_NO_WEB = re.compile(r"\b(?:no|without|not)\s+(?:the\s+)?(?:web|internet|online)\b|\boffline\b", re.I)
_CODE = re.compile(
    r"\b(?:code|codebase|software|library|cli|script|implement\w*|program|repo|repository|pytest|refactor\w*|compile\w*|"
    r"command[- ]line|python package|unit tests?)\b", re.I)
_VAGUE = re.compile(
    r"\b(?:good|great|nice|high[- ]quality|comprehensive|thorough|appropriate|as needed|etc|well[- ]written|professional|"
    r"robust|solid|reasonable|clear|useful)\b", re.I)
_TIERED = re.compile(r"cheap|strong|tier|haiku|draft", re.I)
_NEG_BEFORE = re.compile(r"(?:never|not|n't|no|nobody|cannot|without|nor)\W+(?:\w+\W+){0,3}$", re.I)
_EDITS_OTHERS = re.compile(
    r"\b(?:apply|make|write|put)\w*\s+(?:[\w']+\s+){0,3}(?:corrections?|fixes|changes|edits)\b[^.\n]{0,60}"
    r"|\b(?:edit|modif\w+|overwrit\w+|patch|rewrite|fix|correct)\w*\s+(?:[\w']+\s+){0,3}(?:directly|in place)\b"
    r"|\b(?:directly|in place)\b[^.\n]{0,30}\b(?:edit|modif\w+|correct\w*|fix\w*|updat\w+)"
    r"|\b(?:edit|modif\w+|overwrit\w+|patch|rewrite)\w*\s+(?:[\w']+\s+){0,3}(?:report|draft|file|code|document|deliverable)\b"
    r"|\bapply\w*\s+(?:them|it|these|those|the\s+\w+)\s+to\s+the\s+(?:report|draft|file|code|document|deliverable)\b"
    r"|\bcorrect(?:ed|ions?)?\b[^.\n]{0,25}\bdirectly\b",
    re.I)


def edits_others_files(text: str) -> str | None:
    """The first phrase in ``text`` that tells someone to change another agent's file, or None.

    The runtime lets an agent write only in its own directory, so "apply corrections directly to the report" can
    never be satisfied by a reviewer. Negated phrases ("never edit the report") are fine.
    """
    for m in _EDITS_OTHERS.finditer(text):
        if not _NEG_BEFORE.search(text[max(0, m.start() - 40):m.start()]):
            return m.group(0).strip()
    return None


def _is_code(bp: dict) -> bool:
    kind = _s(_needs(bp).get("kind")).lower()
    if kind:
        return kind == "code"
    d = _deliverable(bp)
    return bool(_CODE.search(" ".join(_s(x) for x in (bp.get("mission"), d.get("description"), d.get("format"),
                                                       (bp.get("task") or {}).get("goal") if isinstance(bp.get("task"), dict) else ""))))


def _blob(bp: dict) -> str:
    n, d = _needs(bp), _deliverable(bp)
    t = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    parts = [bp.get("mission"), n.get("scope"), n.get("sources"), n.get("quality_bar"), d.get("description"),
             d.get("format"), t.get("goal"), *_criteria(bp)]
    return "\n".join(_s(p) for p in parts if p)


def _review_required(needs: dict) -> bool | None:
    r = needs.get("review")
    if r is None or r == "":
        return None
    if isinstance(r, bool):
        return r
    return not re.match(r"\s*(?:no|none|false|not required|skip)\b", _s(r), re.I)


def _has_ws_tools(a: Agent) -> bool:
    return all(t in a.tools for t in WRITE_TOOLS)


# ------------------------------------------------------------------------------------------- validation


def validate(bp: dict, *, org: Org | None = None, allowed_roots: list | None = None) -> list[Issue]:
    """All problems with a blueprint. Errors block ``apply``; warnings are shown in the plan.

    ``org`` supplies the limits (``max_depth``) and the names already taken; ``allowed_roots`` the directories
    agents' workspaces and the deliverable path may be in (default: home, temp dir and the current directory, or
    ``$ORGMCP_WORKSPACE_ROOTS``).
    """
    issues: list[Issue] = []
    if not isinstance(bp, dict):
        return [Issue("error", "", "a blueprint is a mapping with mission, needs, agents and task", "schema")]
    roots = [Path(r).expanduser().resolve() for r in allowed_roots] if allowed_roots else _default_roots()
    cfg = _cfg(org)
    needs, task = bp.get("needs"), bp.get("task")
    _unknown(bp, {"mission", "needs", "agents", "task"}, "blueprint", issues)

    if not _s(bp.get("mission")):
        issues.append(Issue("error", "mission", "write the mission: one paragraph on what the organization is for", "mission"))
    if not isinstance(needs, dict):
        issues.append(Issue("error", "needs", "needs is missing: record the elicited requirements (scope, deliverable, budget, models, review, ...)", "needs"))
        needs = {}
    else:
        _unknown(needs, NEEDS_KEYS, "needs", issues)
    if not isinstance(task, dict):
        issues.append(Issue("error", "task", "task is missing: the first task for root to give (to, title, goal, acceptance)", "task"))
        task = {}
    else:
        _unknown(task, {"to", "title", "goal", "acceptance", "inputs", "budget"}, "task", issues)

    agents = _resolve(bp, org, roots, issues)
    by = {a.addr: a for a in agents}
    tops = [a for a in agents if a.parent is None]
    if not agents:
        issues.append(Issue("error", "agents", "no agents: add the top-level agent (usually a manager) with its team under children", "agents"))
    if len(tops) > 1:
        issues.append(Issue("error", "agents", "exactly one top-level agent is allowed (budget flows down from the agent that gets the task); make the others its children", "agents"))

    # --- structure and limits
    for a in agents:
        if a.depth > int(cfg["max_depth"]):
            issues.append(Issue("error", a.where, f"depth {a.depth} exceeds the organization's max_depth {cfg['max_depth']}; flatten the tree or raise max_depth in ORG.md", "depth"))
        if len(a.children) > a.max_children:
            issues.append(Issue("error", a.where, f"{len(a.children)} children but max_children is {a.max_children}; raise max_children", "children"))
        if a.children and "can_hire" in a.raw and not a.raw["can_hire"]:
            issues.append(Issue("error", a.where, "has children but can_hire is false; the runtime needs can_hire to place them (remove can_hire: false)", "children"))
        if a.children and a.kind not in ("manager", "") and a.template:
            issues.append(Issue("warning", a.where, f"'{a.template.name}' is a {a.kind} template but has children; use the manager template for agents that direct a team", "kind"))
        if org is not None and a.parent is None and org.exists(a.addr):
            issues.append(Issue("error", a.where, f"{a.addr} already exists in this organization; pick another name or retire it first", "exists"))

    # --- authority only narrows down the tree
    for a in agents:
        p = by.get(a.parent) if a.parent else None
        if p is None:
            continue
        extra = sorted(set(a.tools) - set(p.tools))
        if extra:
            issues.append(Issue("error", a.where, f"tools {', '.join(extra)} are not held by its manager {p.addr}; a manager can only grant what it has: add them to {p.addr}'s tools (its charter says it never does the work itself)", "authority"))
        if a.workspace:
            if not p.workspace:
                issues.append(Issue("error", a.where, f"workspace {a.workspace} but its manager {p.addr} has none; give {p.addr} a workspace that contains it", "authority"))
            elif not _within(Path(a.workspace), Path(p.workspace)):
                issues.append(Issue("error", a.where, f"workspace {a.workspace} is not inside its manager's workspace {p.workspace}; the runtime requires reports to work inside it", "authority"))
        bases = [Path(b) for b in (p.workspace, *p.inputs) if b]
        for i in a.inputs:
            if not any(_within(Path(i), b) for b in bases):
                issues.append(Issue("error", a.where, f"input {i} is not inside its manager {p.addr}'s inputs or workspace; a manager can only hand down what it can read: add the path to {p.addr}'s inputs", "authority"))

    # --- inputs are read-only: they must not be inside (or contain) a workspace, or the write fence would not hold
    spaces = sorted({a.workspace for a in agents if a.workspace})
    reported: set[tuple[str, str]] = set()
    for where, raw, ok in declared_inputs(bp):
        ip = Path(os.path.expanduser(raw))
        if ok or not ip.is_absolute() or (where, raw) in reported:
            continue
        reported.add((where, raw))
        ip = ip.resolve()
        hit = next((w for w in spaces if _within(ip, Path(w)) or _within(Path(w), ip)), None)
        if hit:
            issues.append(Issue("error", where, f"input {ip} overlaps the workspace {hit}: inside a workspace it would not be read-only, and a workspace inside an input is only writable because it is the workspace. Use separate directories, or mark the input {{path: {ip}, allow_overlap: true}} if the overlap is intended", "inputs-overlap"))

    # --- what the runtime can and cannot confine (kiro limits read/write by path; shell it cannot)
    for a in agents:
        if "read" in a.tools and not a.workspace and not a.inputs:
            issues.append(Issue("warning", a.where, "has built-in read but no workspace or inputs, so it can read nothing outside the organization; set needs.inputs or needs.workspace if it must read files", "read-nothing"))
    writers = [a.addr for a in agents if "write" in a.tools]
    if writers and not _is_code(bp):
        issues.append(Issue("warning", "agents", f"{', '.join(writers)} hold the built-in write tool for a goal that is not code. kiro confines it to the workspace, but the safer default is orgmcp `write` (agents write in their own directory) plus a deliverable path the assistant copies the final file to; grant write only to an agent that must create files inside the user's own folder", "write-noncode"))
    shells = [a.addr for a in agents if "shell" in a.tools]
    if shells:
        issues.append(Issue("warning", "agents", f"{', '.join(shells)} hold shell. kiro cannot confine shell by path: staying inside the workspace (and leaving inputs alone) is instructed in the charter and prompt, not enforced. Built-in read/write ARE confined; only shell is not", "shell-unconfined"))

    # --- workspace confinement: whoever can write files or run commands is confined to a workspace
    for a in agents:
        if any(t in a.tools for t in WRITE_TOOLS) and not a.workspace:
            issues.append(Issue("error", a.where, f"has {'/'.join(t for t in WRITE_TOOLS if t in a.tools)} but no workspace, so nothing confines what it may touch; set needs.workspace or the agent's workspace", "workspace-confinement"))

    # --- deliverable and exact acceptance criteria
    d = _deliverable(bp)
    crit = _criteria(bp)
    if not _s(d.get("description")):
        issues.append(Issue("error", "needs.deliverable", "state the deliverable: description, format, length and where it should end up (needs.deliverable.description)", "deliverable"))
    else:
        _unknown(d, {"description", "format", "max_words", "path"}, "needs.deliverable", issues)
        if not _s(d.get("format")):
            issues.append(Issue("warning", "needs.deliverable.format", "no format given (e.g. markdown with a comparison table); the writer will guess", "deliverable-format"))
        mw = d.get("max_words")
        if mw is not None and (not isinstance(mw, int) or isinstance(mw, bool) or mw < 1):
            issues.append(Issue("error", "needs.deliverable.max_words", "max_words must be a whole number > 0", "deliverable"))
        elif mw and not any(str(mw) in c for c in crit):
            issues.append(Issue("warning", "task.acceptance", f"the {mw}-word limit is not in any criterion; add an exact criterion such as 'at most {mw} words (as counted by read)'", "limit-criterion"))
    if not isinstance(task.get("acceptance"), list) or not crit:
        issues.append(Issue("error", "task.acceptance", "list the exact, checkable acceptance criteria (numbers, sections, formats, paths) as a YAML list", "criteria"))
    else:
        for i, c in enumerate(crit, 1):
            checkable = re.search(r"\d|[`\"'/]|\b(?:every|each|all|none|only|exactly)\b", c)
            if len(c.split()) < 4 or (_VAGUE.search(c) and not checkable):
                issues.append(Issue("warning", f"task.acceptance[{i}]", f"'{c}' is not checkable; state the exact number, section, format or path that decides pass/fail", "vague-criterion"))
    for k in ("title", "goal"):
        if not _s(task.get(k)):
            issues.append(Issue("error", f"task.{k}", f"task needs a {k}", "task"))
    if task.get("budget") is not None and (not isinstance(task["budget"], int) or isinstance(task["budget"], bool) or task["budget"] < 1):
        issues.append(Issue("error", "task.budget", "budget must be a whole number of runs >= 1", "task"))
    if tops:
        to = _s(task.get("to")) or tops[0].addr
        if to not in by or by[to].parent is not None:
            issues.append(Issue("error", "task.to", f"'{to}' must be the top-level agent ({tops[0].addr}); tasks go to the head of the tree and flow down", "task"))

    # --- deliverable path: how does it get there?
    path = _s(d.get("path"))
    if path:
        p = _check_path(path, "needs.deliverable.path", issues, org, roots, what="deliverable path", dir_must_exist=False)
        if p is not None:
            direct = any(_has_ws_tools(a) and a.workspace and _within(p, Path(a.workspace)) and a.kind == "author" for a in agents)
            if not direct:
                issues.append(Issue("warning", "needs.deliverable.path", f"no agent can write to {p} (agents write only inside their own directory or workspace); the assistant must copy the final artifact there and verify it on completion (the plan lists this step)", "path-delivery"))
            if not p.parent.exists():
                issues.append(Issue("warning", "needs.deliverable.path", f"{p.parent} does not exist; the copy step will create it", "path-parent"))

    # --- tools match the needs
    blob = _blob(bp)
    offline = bool(_NO_WEB.search(_s(needs.get("sources"))))
    web_workers = [a for a in agents if a.kind != "manager" and not a.children and any(t in a.tools for t in WEB_TOOLS)]
    if _WEB_STRONG.search(blob) and not offline:
        if not web_workers:
            issues.append(Issue("error", "needs.sources", "the deliverable needs web sources/URLs but no worker has web_search/web_fetch; use the researcher template (or add tools: [web_search, web_fetch])", "web-tools"))
        elif not any(all(t in a.tools for t in WEB_TOOLS) for a in web_workers):
            issues.append(Issue("warning", "agents", "web research without both web_search and web_fetch: search finds pages, fetch reads them; grant both", "web-tools-partial"))
        if _review_required(needs) and agents and not any(a.kind == "verifier" and any(t in a.tools for t in WEB_TOOLS) for a in agents):
            issues.append(Issue("warning", "agents", "claims are cited from the web but no verifier has web access to re-check them; use the fact-checker template", "verifier-web"))
    elif _WEB_WEAK.search(blob) and not web_workers and not offline and not _is_code(bp):
        issues.append(Issue("warning", "needs.sources", "the text mentions current facts (latest/current/prices/releases) but no agent has web access; confirm that offline work is intended or add a researcher", "web-current"))
    if _is_code(bp):
        if not any(_has_ws_tools(a) and a.workspace and a.kind != "manager" and not a.children for a in agents):
            issues.append(Issue("error", "agents", "a code goal needs an agent with write and shell tools and a workspace (use the engineer template and set needs.workspace)", "code-tools"))
        code = needs.get("code") if isinstance(needs.get("code"), dict) else {}
        for key, what in (("tests", "test runner and what must be tested (e.g. pytest, tests for each criterion)"),
                          ("packaging", "packaging/toolchain (e.g. uv + pyproject)"),
                          ("commits", "commit policy (e.g. commit locally per feature, never push)")):
            if not _s(code.get(key)):
                issues.append(Issue("warning", f"needs.code.{key}", f"not decided: {what}", "code-needs"))
        if crit and not any(re.search(r"\btests?\b|pytest", c, re.I) for c in crit):
            issues.append(Issue("warning", "task.acceptance", "a code goal has no criterion about tests; add one (which command runs them, that they pass)", "code-criteria"))

    # --- review step
    review = _review_required(needs)
    verifiers = [a for a in agents if a.kind == "verifier"]
    authors = [a for a in agents if a.kind == "author"]
    if review is None:
        issues.append(Issue("warning", "needs.review", "review not decided: set needs.review to true (independent check) or false; no independent verifier is planned" if not verifiers else "review not decided: set needs.review to true (independent check) or false", "review"))
    elif review and not verifiers:
        issues.append(Issue("error", "agents", "review is required but there is no reviewer distinct from the author; add a fact-checker, reviewer, code-reviewer or tester agent (a different agent from whoever writes)", "review"))
    elif review and not authors:
        issues.append(Issue("error", "agents", "review is required but nothing to review: no agent produces the work; add a researcher, writer or engineer", "review"))
    # --- reviewers must not be told to edit others' files
    for a in agents:
        texts = [a.extra] if a.extra else []
        if a.kind == "verifier" or "review" in a.name or "check" in a.name:
            hit = next((h for h in map(edits_others_files, texts) if h), None)
            if hit:
                issues.append(Issue("error", a.where, f"charter tells the {a.kind or 'reviewer'} to change another agent's file ('{hit}'), which the single-writer rule (ORG.md rule 9) forbids; make it report findings and required changes to its manager, who sends them to the author", "edits-others"))
    vwords = re.compile(r"\b(?:review\w*|fact-?check\w*|checker|tester|verif\w+|" + "|".join(re.escape(v.name) for v in verifiers) + r")\b", re.I) if verifiers else None
    for i, c in enumerate(crit, 1):
        hit = edits_others_files(c)
        if hit and vwords and vwords.search(c):
            issues.append(Issue("error", f"task.acceptance[{i}]", f"'{hit}': a reviewer cannot change another agent's file; say that the reviewer reports findings and the author applies them", "edits-others"))

    # --- budget
    est = estimate(agents) if agents else {"total": 0, "per": {}}
    cap = needs.get("budget_runs")
    total = planned_total(bp, est["total"]) if agents else 0
    if cap is None:
        issues.append(Issue("warning", "needs.budget_runs", f"no budget cap from the user; the estimate is {est['total']} runs: ask what they are willing to spend", "budget"))
    elif not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        issues.append(Issue("error", "needs.budget_runs", "budget_runs must be a whole number of runs >= 1", "budget"))
        cap = None
    if agents and isinstance(task.get("budget"), int) and not isinstance(task.get("budget"), bool):
        total = task["budget"]
    if cap is not None and total > cap:
        issues.append(Issue("error", "task.budget", f"planned budget {total} runs is above the user's cap of {cap}; lower task.budget or shrink the team", "budget-cap"))
    if agents and total < est["total"]:
        issues.append(Issue("error", "task.budget" if task.get("budget") else "needs.budget_runs", f"{total} runs cannot cover the pipeline: the estimate with one review and one rework cycle is {est['total']} (see estimate()); raise the budget or drop a role", "budget-low"))
    elif agents and total < math.ceil(est["total"] * TIGHT):
        issues.append(Issue("warning", "task.budget", f"{total} runs leaves almost no slack over the estimate of {est['total']}; expect a stall on the first surprise", "budget-tight"))

    # --- models
    pol = _s(needs.get("model_policy"))
    if not pol:
        issues.append(Issue("warning", "needs.model_policy", "no model policy: decide cheap drafting + strong review, or one model for everyone", "model-policy"))
    elif _TIERED.search(pol) and not re.match(r"\s*(?:single|same|one|default)\b", pol, re.I) and len(agents) > 1:
        if len({a.model for a in agents}) < 2:
            issues.append(Issue("error", "agents", f"model policy '{pol}' asks for different models for drafting and review, but all agents use the same one; set needs.models {{cheap, strong}} (and give reviewers model: strong)", "model-single"))
        else:
            weak = [a for a in verifiers if authors and {a.model} == {x.model for x in authors}]
            if weak:
                issues.append(Issue("warning", weak[0].where, "the reviewer uses the same model as the author it checks; the policy asks for a stronger reviewer (model: strong)", "model-review"))

    # --- elicited preferences the org itself does not use but the assistant must honor
    for key, hint in (("scope", "what is in and out of scope"), ("approval", "when the user wants to approve (plan, before start, final)"),
                      ("progress", "how the user wants progress updates")):
        if not _s(needs.get(key)):
            issues.append(Issue("warning", f"needs.{key}", f"not elicited: {hint}", f"needs-{key}"))
    return issues


# --------------------------------------------------------------------------------------------- charters


def _charter(a: Agent, agents: list[Agent], bp: dict, split: dict[str, dict]) -> str:
    by = {x.addr: x for x in agents}
    needs, d = _needs(bp), _deliverable(bp)
    parts = [a.template.body] if a.template else []
    asg = ["## Assignment (from the approved plan)", f"Mission: {_s(bp.get('mission'))}"]
    if d.get("description"):
        spec = ", ".join(x for x in (_s(d.get("format")), f"at most {d['max_words']} words" if d.get("max_words") else "") if x)
        asg.append(f"Deliverable: {_s(d['description'])}" + (f" ({spec})" if spec else ""))
    if a.parent is None and d.get("path"):
        asg.append(f"The assistant copies the final artifact to {_s(d['path'])} after you report; name the artifact's path in your report.")
    if _s(needs.get("quality_bar")):
        asg.append(f"Quality bar: {_s(needs['quality_bar'])}")
    if _s(needs.get("scope")):
        asg.append(f"Scope: {_s(needs['scope'])}")
    if a.workspace:
        asg.append(f"Workspace: {a.workspace}. Everything you read, write or run outside orgmcp stays inside it; nothing else on the machine, and nothing under ~/.kiro or the organization directory. Relative paths in kiro tools resolve there; your org files (MEMORY.md, work/) are written with orgmcp `write`, never into the workspace.")
    if a.inputs:
        asg.append(f"Read-only inputs: {', '.join(a.inputs)}. Read them (kiro `read`, or orgmcp `read` by absolute path); never create, edit or delete anything there.")
    if "shell" in a.tools:
        asg.append("shell is not confined by the runtime: keep every command inside your workspace, and never write to the inputs, the organization directory or anywhere else.")
    code = needs.get("code") if isinstance(needs.get("code"), dict) else {}
    if _is_code(bp) and a.kind != "manager" and code:
        asg.append("Engineering rules: " + "; ".join(f"{k}: {_s(v)}" for k, v in code.items() if _s(v)))
    asg.append(f"Reports to: {a.parent or 'root (the human)'}")
    if a.children:
        asg.append("Your team (fixed by the plan; you cannot change it):")
        for c in a.children:
            k = by[c]
            asg.append(f"- {c}: {k.role} ({k.kind}; tools: {', '.join(k.tools) or 'none'}; model: {k.model or 'org default'})")
        grants = [(c, split[c]["grant"]) for c in a.children]
        asg += [
            f"Budget plan: you start with {split[a.addr]['grant']} runs. Initial grants, set explicitly with `budget=`: "
            + ", ".join(f"{c} {n}" for c, n in grants) + f". You keep {split[a.addr]['keeps']} runs: your own runs plus the reserve for "
            "one review and one rework cycle (rework tasks hand down 1-2 runs each). Do not hand down more than this up front. Runs you do not spend return to your parent automatically with your final report.",
        ]
        vs = [c for c in a.children if by[c].kind == "verifier"]
        if vs:
            au = [c for c in a.children if by[c].kind == "author"]
            asg.append(f"Review loop: {', '.join(au) or 'the authors'} produce; {', '.join(vs)} verif{'ies' if len(vs) == 1 else 'y'} independently and report findings and required changes to you; "
                       "you send them to the author with `revises`; verifiers never edit the author's file.")
    parts.append("\n".join(asg))
    if a.extra:
        parts.append(("## Additional instructions\n" if a.template else "") + a.extra)
    return "\n\n".join(parts)


# ----------------------------------------------------------------------------------------------- plan


def _access(a: Agent) -> str:
    """One line on what the runtime lets this agent reach with kiro's file tools (and what it only instructs)."""
    bits = []
    if "write" in a.tools:
        bits.append(f"kiro write only in {a.workspace}" if a.workspace else "kiro write nowhere")
    if "read" in a.tools:
        bases = [b for b in (a.workspace, *a.inputs) if b]
        bits.append("kiro read only in " + ", ".join(bases) if bases else "kiro read nowhere")
    if a.inputs and "read" not in a.tools:
        bits.append("read-only inputs (orgmcp read): " + ", ".join(a.inputs))
    if "shell" in a.tools:
        bits.append("shell NOT confined (instructed only)")
    return "; ".join(bits)


def _tree_lines(agents: list[Agent]) -> list[str]:
    by = {a.addr: a for a in agents}
    out: list[str] = []

    def line(a: Agent, indent: int) -> None:
        tpl = f"[{a.template.name}]" if a.template else "[custom]"
        ws = f" ws={a.workspace}" if a.workspace else ""
        out.append(f"{'  ' * indent}- {a.name} {tpl} {a.role}: model={a.model or 'org default'}, tools={','.join(a.tools) or 'none'}{ws}")
        access = _access(a)
        if access:
            out.append(f"{'  ' * indent}  Access: {access}")
        for c in a.children:
            line(by[c], indent + 1)

    for a in agents:
        if a.parent is None:
            line(a, 0)
    return out


def render_plan(bp: dict, issues: list[Issue] | None = None, *, org: Org | None = None, allowed_roots: list | None = None) -> str:
    """The plan the user approves: goal, needs, org tree, budget, review, deliverable, checkpoints, warnings."""
    if issues is None:
        issues = validate(bp, org=org, allowed_roots=allowed_roots)
    roots = [Path(r).expanduser().resolve() for r in allowed_roots] if allowed_roots else _default_roots()
    scratch: list[Issue] = []
    agents = _resolve(bp, org, roots, scratch)
    needs, d = _needs(bp), _deliverable(bp)
    task = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    errs = [i for i in issues if i.level == "error"]
    warns = [i for i in issues if i.level == "warning"]
    mission = _s(bp.get("mission")) or "(missing)"
    L: list[str] = ["# Plan for approval", "", f"Goal: {mission}", "", "Needs as understood:"]

    def need(label: str, value) -> None:
        L.append(f"- {label}: {_s(value) or '(not specified)'}")

    need("Scope", needs.get("scope"))
    spec = ", ".join(x for x in (_s(d.get("format")), f"max {d['max_words']} words" if d.get("max_words") else "") if x)
    need("Deliverable", (_s(d.get("description")) + (f" [{spec}]" if spec else "")) if d.get("description") else "")
    need("Quality bar", needs.get("quality_bar"))
    need("Sources / tools", needs.get("sources"))
    need("Workspace", needs.get("workspace") or "none (no agent writes files or runs commands)")
    if _is_code(bp):
        code = needs.get("code") if isinstance(needs.get("code"), dict) else {}
        need("Tests / packaging / commits", "; ".join(f"{k}: {_s(code.get(k)) or '?'}" for k in ("tests", "packaging", "commits")))
    need("Model policy", needs.get("model_policy"))
    r = _review_required(needs)
    need("Review", "required" if r else ("not required" if r is False else None))

    L += ["", f"Organization ({len(agents)} agents):"]
    L += _tree_lines(agents) or ["- (none)"]

    est = estimate(agents) if agents else {"total": 0, "per": {}}
    total = planned_total(bp, est["total"]) if agents else 0
    if isinstance(task.get("budget"), int):
        total = task["budget"]
    cap = needs.get("budget_runs")
    L += ["", f"Budget: {total} runs planned" + (f" (your cap: {cap})" if cap else " (no cap given)")
          + f", estimate {est['total']} for one pass + one review/rework cycle:",
          "  This is a ceiling: runs the team does not spend come back automatically, agent by agent, with their final reports, until what is left returns to you."]
    if agents:
        split = budget_split(agents, total)
        by_addr = {x.addr: x for x in agents}
        for a in agents:
            e = est["per"][a.addr]
            if a.children:
                keeps = split[a.addr]["keeps"]
                held = sum(est["per"][c]["rework"] for c in a.children if not by_addr[c].children)
                L.append(f"  {a.addr}: starts with {split[a.addr]['grant']}, hands down "
                         + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                         + f", keeps {keeps} (own {e['total']} + rework runs for reports {held}"
                         + (f" + slack {keeps - e['total'] - held})" if keeps - e["total"] - held else ")"))
            else:
                L.append(f"  {a.addr}: {split[a.addr]['grant']} runs ({e['pass']} work + {e['rework']} rework)")
    else:
        split = {}

    verifiers = [a for a in agents if a.kind == "verifier"]
    L += ["", "Review / verification:"]
    if verifiers:
        authors = [a for a in agents if a.kind == "author"]
        L += [f"- {', '.join(v.addr for v in verifiers)} check{'s' if len(verifiers) == 1 else ''} the work of {', '.join(x.addr for x in authors) or 'the team'} independently;"
              " findings go to their manager, who sends required changes back to the author (nobody edits another agent's file)."]
    else:
        L.append("- no independent reviewer" + (" (review not requested)" if r is False else " (!)"))
    L.append("- the assistant re-checks the final deliverable against every acceptance criterion before telling you it is done")

    L += ["", "Deliverable:"]
    L.append(f"- {_s(d.get('description')) or '(missing)'}" + (f" ({spec})" if spec else ""))
    if _s(d.get("path")):
        copy = any(i.code == "path-delivery" for i in issues)
        L.append(f"- Final location: {_s(d['path'])}" + (" (copied there by the assistant after verification)" if copy else " (written there by the team)"))
    else:
        L.append("- Final location: inside the organization (no path given)")

    L += ["", f"First task: to {_s(task.get('to')) or (agents[0].addr if agents else '?')}: {_s(task.get('title')) or '(missing)'}"]
    crit = _criteria(bp)
    L += [f"  {i}. {c}" for i, c in enumerate(crit, 1)] or ["  (no acceptance criteria)"]

    L += ["", "Checkpoints:",
          f"- Approval: {_s(needs.get('approval')) or 'plan approval before anything is built or started (default)'}",
          f"- Progress: {_s(needs.get('progress')) or 'one line on request (default)'}",
          "- Any spend beyond the budget needs your OK."]

    if warns:
        L += ["", f"Warnings ({len(warns)}):"] + [f"- {w.path}: {w.message}" for w in warns]
    if errs:
        L += ["", f"Errors ({len(errs)}) - must be fixed before this can be applied:"] + [f"- {e.path}: {e.message}" for e in errs]
    L.append("")
    L.append("Cannot apply yet: tell me what to change." if errs else "Reply 'approve' or tell me what to change.")
    return "\n".join(L)


# ------------------------------------------------------------------------------- plan for the user

PLAN_HEADING = "PLAN FOR YOU (show this to the user exactly as written)"
PLAN_DRAFT_HEADING = "DRAFT - NOT READY (it has errors: fix the blueprint and propose again; do not show this to the user)"
PLAN_END = "END OF PLAN FOR YOU"
TOOL_WORDS = {"read": "read files", "write": "write files", "shell": "run commands", "web_search": "search the web",
              "web_fetch": "read web pages"}
SHOWN_CRITERIA = 8  # the block stays compact (about 40 lines); the full lists are in the details
SHOWN_WARNINGS = 5
HIDDEN_WARNINGS = {"path-delivery", "path-parent", "needs-scope", "needs-approval", "needs-progress"}  # said elsewhere in the block
PLAN_ID_LENGTH = 12


def plan_id(bp: dict) -> str:
    """A short stable hash of the normalized blueprint: the same blueprint (whatever its YAML layout, comments or
    key order) always gives the same id; any change to a value gives another. ``apply_org`` requires it, so what is
    applied is what ``propose_org`` showed. Stateless: nothing is stored, it survives restarts."""
    canon = json.dumps(_normalize(bp), sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:PLAN_ID_LENGTH]


def _clip(text: str, limit: int = 220) -> str:
    text = " ".join(_s(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _agent_access(a: Agent) -> str:
    """What the agent may touch, in plain words (one phrase; the one place to extend with more access detail)."""
    tools = ", ".join(TOOL_WORDS.get(t, t) for t in a.tools)
    if a.kind == "manager" or a.children:
        return "directs the team; does not produce the work itself"
    changes = any(t in a.tools for t in WRITE_TOOLS)
    where = (f"changes files only in {a.workspace}" if a.workspace else "changes files only in its own folder") if changes \
        else "cannot change your files"
    return f"can {tools}; {where}" if tools else f"uses no tools; {where}"


def _user_tree(agents: list[Agent]) -> list[str]:
    by = {a.addr: a for a in agents}
    out: list[str] = []

    def line(a: Agent, indent: int) -> None:
        out.append(f"{'  ' * indent}- {a.name} ({a.role}, model {a.model or 'org default'}): {_agent_access(a)}")
        for c in a.children:
            line(by[c], indent + 1)

    for a in agents:
        if a.parent is None:
            line(a, 0)
    return out


def _user_budget(agents: list[Agent], bp: dict) -> list[str]:
    needs, task = _needs(bp), bp.get("task") if isinstance(bp.get("task"), dict) else {}
    est = estimate(agents) if agents else {"total": 0, "per": {}}
    total = planned_total(bp, est["total"]) if agents else 0
    cap = needs.get("budget_runs")
    out = [f"Budget: {total} runs planned (one run = one working session of one agent), "
           + (f"your cap is {cap}" if cap else "you gave no cap") + f"; the minimum for one review and rework is {est['total']}. "
           "Unspent runs come back to you."]
    if agents:
        split = budget_split(agents, total)
        for a in agents:
            if a.children:
                out.append(f"  {a.addr} starts with {split[a.addr]['grant']}, hands down "
                           + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                           + f" and keeps {split[a.addr]['keeps']} for planning, checking and rework.")
    return out


def plan_for_user(bp: dict, issues: list[Issue] | None = None, *, org: Org | None = None, allowed_roots: list | None = None) -> str:
    """The compact, plain-language plan the assistant shows to the user verbatim (about 40 lines at most).

    Goal, needs as understood, the team (role, model, tools, access), budget and its split, review, deliverable and
    where it will be delivered, the success checks, checkpoints and warnings. ``render_plan`` has the full details.
    """
    if issues is None:
        issues = validate(bp, org=org, allowed_roots=allowed_roots)
    roots = [Path(r).expanduser().resolve() for r in allowed_roots] if allowed_roots else _default_roots()
    agents = _resolve(bp, org, roots, [])
    needs, d = _needs(bp), _deliverable(bp)
    task = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    errs = [i for i in issues if i.level == "error"]
    warns = [i for i in issues if i.level == "warning" and i.code not in HIDDEN_WARNINGS]
    L: list[str] = [PLAN_DRAFT_HEADING if errs else PLAN_HEADING, f"Goal: {_clip(bp.get('mission')) or '(missing)'}", "What I understood you need:"]

    def need(label: str, value) -> None:
        L.append(f"- {label}: {_clip(value) or '(not specified)'}")

    need("Scope", needs.get("scope"))
    if _list(needs.get("inputs")):
        need("Your files (read-only)", ", ".join(_list(needs.get("inputs"))))
    need("Quality bar", needs.get("quality_bar"))
    if _s(needs.get("sources")) or not _is_code(bp):
        need("Sources", needs.get("sources"))
    need("Workspace", needs.get("workspace") or "none (nothing writes files or runs commands)")
    if _is_code(bp):
        code = needs.get("code") if isinstance(needs.get("code"), dict) else {}
        need("Tests / packaging / commits", "; ".join(f"{k}: {_s(code.get(k)) or '?'}" for k in ("tests", "packaging", "commits")))
    need("Models", needs.get("model_policy"))

    L.append(f"Team ({len(agents)} agents):")
    L += _user_tree(agents) or ["- (none)"]
    L += _user_budget(agents, bp)

    verifiers = [a for a in agents if a.kind == "verifier"]
    r = _review_required(needs)
    if verifiers:
        L.append("Checking: " + ", ".join(v.name for v in verifiers) + " review"
                 + ("s" if len(verifiers) == 1 else "") + " the work independently (they did not write it); required changes go back "
                 "to the author. I then re-check the final result against every success check below.")
    else:
        L.append("Checking: no independent reviewer" + (" (you did not ask for one)" if r is False else " (!)")
                 + ". I still re-check the final result against every success check below.")

    spec = ", ".join(x for x in (_s(d.get("format")), f"max {d['max_words']} words" if d.get("max_words") else "") if x)
    L.append(f"Deliverable: {_clip(d.get('description')) or '(missing)'}" + (f" [{spec}]" if spec else ""))
    if _s(d.get("path")):
        copied = any(i.code == "path-delivery" for i in issues)
        L.append(f"  Delivered to: {_s(d['path'])}" + (" (I copy it there after checking it)" if copied else " (the team writes it there)"))
    elif _s(needs.get("workspace")) and _is_code(bp):
        L.append(f"  Delivered to: the workspace {_s(needs['workspace'])} (the team works and commits there)")
    else:
        L.append("  Delivered to: inside the organization folder (no location given)")

    crit = _criteria(bp)
    L.append("Done when ALL of these hold:" if crit else "Done when: (no success checks given)")
    L += [f"  {i}. {_clip(c, 200)}" for i, c in enumerate(crit[:SHOWN_CRITERIA], 1)]
    if len(crit) > SHOWN_CRITERIA:
        L.append(f"  ... and {len(crit) - SHOWN_CRITERIA} more (see the details)")

    L.append(f"Checkpoints: approval - {_clip(needs.get('approval')).rstrip('.') or 'this plan, before anything is built or started'}; "
             f"progress - {_clip(needs.get('progress')).rstrip('.') or 'one line when you ask'}; any spend beyond the budget needs your OK.")
    if warns:
        L.append(f"Warnings ({len(warns)}):")
        L += [f"- {_clip(w.message, 200)}" for w in warns[:SHOWN_WARNINGS]]
        if len(warns) > SHOWN_WARNINGS:
            L.append(f"- ... and {len(warns) - SHOWN_WARNINGS} more (see the details)")
    if errs:
        L.append(f"Errors ({len(errs)}):")
        L += [f"- {e.path}: {_clip(e.message, 200)}" for e in errs[:SHOWN_WARNINGS]]
    L.append("Nothing is created or started until you approve. Reply 'approve', or tell me what to change." if not errs
             else "Cannot apply yet.")
    L.append(PLAN_END)
    return "\n".join(L)


def propose_text(bp: dict, org: Org | None = None, *, target: str = "", allowed_roots: list | None = None) -> str:
    """What ``propose_org`` returns: the block for the user, the full details and the plan_id."""
    issues = validate(bp, org=org, allowed_roots=allowed_roots)
    block = plan_for_user(bp, issues, org=org, allowed_roots=allowed_roots)
    details = render_plan(bp, issues, org=org, allowed_roots=allowed_roots)
    if errors(issues):
        nxt = "plan_id: none (the blueprint has errors). Fix them and call propose_org again; do not ask the user to approve this."
    else:
        pid = plan_id(bp)
        nxt = (f"plan_id: {pid}\nNext: show the PLAN FOR YOU block above to the user exactly as written (a plain-words intro line "
               f"before it is fine) and wait for their explicit approval. Then apply_org(blueprint=<this exact YAML>, "
               f"approved=True, plan_id=\"{pid}\"). If you change the blueprint, call propose_org again: the plan_id changes.")
    return "\n\n".join(x for x in (target, block, "Details (the full plan, for you; the user need not read it):\n" + details, nxt) if x)


def propose(source, *, org: Org | None = None, allowed_roots: list | None = None) -> str:
    """Load a blueprint (text, path or dict), validate it and return the plan text. Writes nothing."""
    bp = load(source)
    return render_plan(bp, validate(bp, org=org, allowed_roots=allowed_roots), org=org, allowed_roots=allowed_roots)


# ----------------------------------------------------------------------------------------------- apply


@dataclass
class Summary:
    agents: list[str]
    task_id: str
    to: str
    budget: int
    warnings: list[Issue] = field(default_factory=list)

    def text(self) -> str:
        lines = [f"created {len(self.agents)} agents: {', '.join(self.agents)}",
                 f"task {self.task_id} -> {self.to} (budget {self.budget})"]
        lines += [f"warning: {w.path}: {w.message}" for w in self.warnings]
        return "\n".join(lines)


def apply(org: Org, bp: dict, *, allowed_roots: list | None = None) -> Summary:
    """Create the agents (parents first, as root through each parent) and give the first task.

    Refuses on any validation error or existing name, before writing anything. If a hire or the delegation fails
    midway, everything created is retired again and the error is raised.
    """
    issues = validate(bp, org=org, allowed_roots=allowed_roots)
    errs = errors(issues)
    if errs:
        raise BlueprintError("blueprint has errors, nothing was created:\n" + "\n".join(f"- {i.path}: {i.message}" for i in errs))
    roots = [Path(r).expanduser().resolve() for r in allowed_roots] if allowed_roots else _default_roots()
    agents = _resolve(bp, org, roots, [])
    task = bp["task"]
    est = estimate(agents)
    total = planned_total(bp, est["total"])
    split = budget_split(agents, total)
    top = agents[0]
    made_dirs: list[Path] = []
    created: list[str] = []
    try:
        for a in agents:  # parents before children
            if a.workspace and not Path(a.workspace).exists():
                p = Path(a.workspace)
                missing = [q for q in (p, *p.parents) if not q.exists()]
                p.mkdir(parents=True, exist_ok=True)
                made_dirs += missing
            addr = org.hire(
                a.parent or ROOT, a.name, a.role, _charter(a, agents, bp, split), model=a.model, tools=a.tools,
                can_hire=a.can_hire, max_children=a.max_children, workspace=a.workspace,
                inputs=a.inputs if (a.inputs or "read" in a.tools) else None,
            )
            created.append(addr)
        crit = _criteria(bp)
        acceptance = "\n".join(f"{i}. {c}" for i, c in enumerate(crit, 1))
        goal = _s(task.get("goal"))
        d = _deliverable(bp)
        if d.get("description"):
            spec = ", ".join(x for x in (_s(d.get("format")), f"at most {d['max_words']} words" if d.get("max_words") else "") if x)
            goal += f"\n\nDeliverable: {_s(d['description'])}" + (f" ({spec})" if spec else "") + ". Report its path as an artifact."
        msg = org.delegate(ROOT, top.addr, _s(task["title"]), goal, acceptance, _list(task.get("inputs")), total)
    except Exception:
        for addr in reversed(created):
            if org.exists(addr) and Org.depth(addr) == 1:
                try:
                    org.retire(ROOT, addr, "blueprint apply failed midway; rolled back")
                except OrgError:
                    pass
        for p in made_dirs:  # directories this call created, if still empty
            try:
                p.rmdir()
            except OSError:
                break
        raise
    org.commit(f"root: applied blueprint ({len(created)} agents), task {msg.id} -> {top.addr}")
    return Summary(created, msg.id, top.addr, total, [i for i in issues if i.level == "warning"])
