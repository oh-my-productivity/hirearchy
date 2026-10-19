"""``RuleBlueprintValidator``: what went wrong in the usability studies, as checks over a blueprint.

Errors block ``apply``; warnings are shown in the plan."""

from __future__ import annotations

import math
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from ..kernel import JsonObject, inside
from ..settings import config_default_model
from ._budgeting import TIGHT
from ._protocols import AccessReport, AgentResolution, BudgetPlanning, OrgContexts, PathChecking, ServiceRules, WorkspaceRoots
from ._resolver import declared_inputs, review_roots
from ._rules import (
    NO_WEB,
    TIERED,
    WEB_STRONG,
    WEB_WEAK,
    blob,
    delivers_directly,
    edits_others_files,
    has_ws_tools,
    is_code,
    review_required,
    vague,
)
from ._shapes import Estimate
from ._view import (
    NEEDS_KEYS,
    REQUEST_KEYS,
    TASK_KEYS,
    WEB_TOOLS,
    WRITE_TOOLS,
    criteria_of,
    deliverable_of,
    is_plain,
    mapping_or_empty,
    s,
    services_of,
    svc_criteria,
    unknown,
)
from .api import BlueprintValidator, Issue


class RuleBlueprintValidator(BlueprintValidator):
    def __init__(
        self, resolver: AgentResolution, paths: PathChecking, budgets: BudgetPlanning, access: AccessReport, services: ServiceRules,
        roots: WorkspaceRoots, orgs: OrgContexts,
    ) -> None:
        self._resolver = resolver
        self._paths = paths
        self._budgets = budgets
        self._access = access
        self._services = services
        self._roots = roots
        self._orgs = orgs

    def validate(
        self, bp: Mapping[str, object], *, org_exists: bool = False, allowed_roots: Sequence[str | Path] | None = None,
    ) -> list[Issue]:
        issues: list[Issue] = []
        if not isinstance(bp, dict):
            return [Issue("error", "", "a blueprint is a mapping with mission, needs, agents and task", "schema")]
        org = self._orgs.context(org_exists)
        roots = self._roots.roots(allowed_roots)
        cfg = org.config()
        raw_needs, raw_task = bp.get("needs"), bp.get("task")
        unknown(bp, {"mission", "needs", "agents", "task", "services"}, "blueprint", issues)
        services = services_of(bp)
        plain = is_plain(bp)

        if not s(bp.get("mission")):
            issues.append(Issue("error", "mission", "write the mission: one paragraph on what the organization is for", "mission"))
        needs: JsonObject
        if not isinstance(raw_needs, dict):
            issues.append(Issue("error", "needs", "needs is missing: record the elicited requirements (scope, deliverable, budget, models, review, ...)", "needs"))
            needs = {}
        else:
            needs = raw_needs
            unknown(needs, NEEDS_KEYS, "needs", issues)
        task: JsonObject
        if not isinstance(raw_task, dict):
            if raw_task is not None or not services:
                issues.append(Issue("error", "task", "task is missing: the first task for root to give (to, title, goal, acceptance). For recurring work, offer it as a standing service instead: add `services:` (see blueprint_example(kind, service=True))", "task"))
            task = {}
        else:
            task = raw_task
            unknown(task, REQUEST_KEYS if "service" in task else TASK_KEYS, "task", issues)

        agents = self._resolver.resolve(bp, org, roots, issues)
        by = {a.addr: a for a in agents}
        tops = [a for a in agents if a.parent is None]
        if not agents:
            issues.append(Issue("error", "agents", "no agents: add the top-level agent (usually a manager) with its team under children", "agents"))
        if len(tops) > 1:
            issues.append(Issue("error", "agents", "exactly one top-level agent is allowed (budget flows down from the agent that gets the task); make the others its children", "agents"))

        # --- structure and limits
        for a in agents:
            if a.depth > int(cast("int | str", cfg["max_depth"])):
                issues.append(Issue("error", a.where, f"depth {a.depth} exceeds the organization's max_depth {cfg['max_depth']}; flatten the tree or raise max_depth in ORG.md", "depth"))
            if len(a.children) > a.max_children:
                issues.append(Issue("error", a.where, f"{len(a.children)} children but max_children is {a.max_children}; raise max_children", "children"))
            if a.children and "can_hire" in a.raw and not a.raw["can_hire"]:
                issues.append(Issue("error", a.where, "has children but can_hire is false; the runtime needs can_hire to place them (remove can_hire: false)", "children"))
            if a.children and a.kind not in ("manager", "") and a.template:
                issues.append(Issue("warning", a.where, f"'{a.template.name}' is a {a.kind} template but has children; use the manager template for agents that direct a team", "kind"))
            if a.parent is None and org.exists(a.addr):
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
                elif not inside(Path(a.workspace), Path(p.workspace)):
                    issues.append(Issue("error", a.where, f"workspace {a.workspace} is not inside its manager's workspace {p.workspace}; the runtime requires reports to work inside it", "authority"))
            bases = [Path(b) for b in (p.workspace, *p.inputs) if b]
            for held_input in a.inputs:
                if not any(inside(Path(held_input), b) for b in bases):
                    issues.append(Issue("error", a.where, f"input {held_input} is not inside its manager {p.addr}'s inputs or workspace; a manager can only hand down what it can read: add the path to {p.addr}'s inputs", "authority"))

        # --- inputs are read-only: they must not be inside (or contain) a workspace, or the write fence would not hold
        spaces = sorted({a.workspace for a in agents if a.workspace})
        reported: set[tuple[str, str]] = set()
        for where, raw, ok in declared_inputs(bp):
            ip = Path(os.path.expanduser(raw))
            if ok or not ip.is_absolute() or (where, raw) in reported:
                continue
            reported.add((where, raw))
            ip = ip.resolve()
            hit = next((w for w in spaces if inside(ip, Path(w)) or inside(Path(w), ip)), None)
            if hit:
                issues.append(Issue("error", where, f"input {ip} overlaps the workspace {hit}: inside a workspace it would not be read-only, and a workspace inside an input is only writable because it is the workspace. Use separate directories, or mark the input {{path: {ip}, allow_overlap: true}} if the overlap is intended", "inputs-overlap"))

        # --- what the runtime can and cannot confine (kiro limits read/write by path; shell it cannot)
        for a in agents:
            if "read" in a.tools and not a.workspace and not a.inputs:
                issues.append(Issue("warning", a.where, "has built-in read but no workspace or inputs, so it can read nothing outside the organization; set needs.inputs or needs.workspace if it must read files", "read-nothing"))
        writers = [a.addr for a in agents if "write" in a.tools]
        if writers and not is_code(bp):
            issues.append(Issue("warning", "agents", f"{', '.join(writers)} hold the built-in write tool for a goal that is not code. kiro confines it to the workspace, but the safer default is orgmcp `write` (agents write in their own directory) plus a deliverable path the assistant copies the final file to; grant write only to an agent that must create files inside the user's own folder", "write-noncode"))
        shells = [a.addr for a in agents if "shell" in a.tools]
        if shells:
            issues.append(Issue("warning", "agents", f"{', '.join(shells)} hold shell. kiro cannot confine shell by path: staying inside the workspace (and leaving inputs alone) is instructed in the charter and prompt, not enforced. Built-in read/write ARE confined; only shell is not", "shell-unconfined"))

        # --- a verifier reads what it reviews (the default gives it the project and authors' workspaces read-only)
        ws_text = s(needs.get("workspace"))
        pws = Path(os.path.expanduser(ws_text)).resolve() if ws_text and Path(os.path.expanduser(ws_text)).is_absolute() else None
        work = review_roots(agents, pws)
        if any(inside(r, pws) and r != pws for r in work if pws):
            work = [r for r in work if r != pws]  # the authors' own folders stand for the project folder
        for a in agents:
            if a.kind != "verifier" or a.children:
                continue
            held = [Path(b) for b in (a.workspace, *a.inputs) if b]
            blind = [r for r in work if not any(inside(r, b) for b in held)]
            if blind:
                issues.append(Issue("warning", a.where, f"{a.addr} reviews work in {', '.join(map(str, blind))} but cannot read it (not in its workspace or inputs), so it would review pasted text, not the files; drop its explicit inputs (by default a verifier gets the project and authors' workspaces read-only) or add the path", "verifier-cannot-read"))
        # an author without a write tool leaves its work in its org folder (`<addr>/work/`): the verifier must be able to open it
        org_authors = [a.addr for a in agents if a.kind == "author" and not any(t in a.tools for t in WRITE_TOOLS)]
        if org_authors:
            for a in agents:
                if a.kind == "verifier" and not a.children and not self._access.org_files_readable(a):
                    issues.append(Issue("warning", a.where, f"{a.addr} reviews work that {', '.join(org_authors)} leave in the organization's folders, but its tools cannot read the organization's files, so it would review pasted text, not the files; give it orgmcp read (leave out the built-in read) or make the files reachable", "verifier-cannot-read"))

        # --- workspace confinement: whoever can write files or run commands is confined to a workspace
        for a in agents:
            if any(t in a.tools for t in WRITE_TOOLS) and not a.workspace:
                issues.append(Issue("error", a.where, f"has {'/'.join(t for t in WRITE_TOOLS if t in a.tools)} but no workspace, so nothing confines what it may touch; set needs.workspace or the agent's workspace", "workspace-confinement"))

        # --- deliverable and exact acceptance criteria (a services-only blueprint states them per service, below)
        d = deliverable_of(bp)
        crit = criteria_of(bp)
        if not s(d.get("description")):
            if plain:
                issues.append(Issue("error", "needs.deliverable", "state the deliverable: description, format, length and where it should end up (needs.deliverable.description)", "deliverable"))
        else:
            unknown(d, {"description", "format", "max_words", "path"}, "needs.deliverable", issues)
            if not s(d.get("format")):
                issues.append(Issue("warning", "needs.deliverable.format", "no format given (e.g. markdown with a comparison table); the writer will guess", "deliverable-format"))
            mw = d.get("max_words")
            if mw is not None and (not isinstance(mw, int) or isinstance(mw, bool) or mw < 1):
                issues.append(Issue("error", "needs.deliverable.max_words", "max_words must be a whole number > 0", "deliverable"))
            elif mw and plain and not any(str(mw) in c for c in crit):
                issues.append(Issue("warning", "task.acceptance", f"the {mw}-word limit is not in any criterion; add an exact criterion such as 'at most {mw} words (as counted by read)'", "limit-criterion"))
        if plain:
            if not isinstance(task.get("acceptance"), list) or not crit:
                issues.append(Issue("error", "task.acceptance", "list the exact, checkable acceptance criteria (numbers, sections, formats, paths) as a YAML list", "criteria"))
            else:
                vague(crit, "task.acceptance", issues)
            for k in ("title", "goal"):
                if not s(task.get(k)):
                    issues.append(Issue("error", f"task.{k}", f"task needs a {k}", "task"))
            task_budget = task.get("budget")
            if task_budget is not None and (not isinstance(task_budget, int) or isinstance(task_budget, bool) or task_budget < 1):
                issues.append(Issue("error", "task.budget", "budget must be a whole number of runs >= 1", "task"))
            if tops:
                to = s(task.get("to")) or tops[0].addr
                if to not in by or by[to].parent is not None:
                    issues.append(Issue("error", "task.to", f"'{to}' must be the top-level agent ({tops[0].addr}); tasks go to the head of the tree and flow down", "task"))

        # --- deliverable path: how does it get there?
        path = s(d.get("path"))
        if path:
            target = self._paths.check(path, "needs.deliverable.path", issues, org, roots, what="deliverable path", dir_must_exist=False)
            if target is not None:
                if not delivers_directly(agents, target):
                    issues.append(Issue("warning", "needs.deliverable.path", f"no agent can write to {target} (agents write only inside their own directory or workspace); the assistant must copy the final artifact there and verify it on completion (the plan lists this step)", "path-delivery"))
                if not target.parent.exists():
                    issues.append(Issue("warning", "needs.deliverable.path", f"{target.parent} does not exist; the copy step will create it", "path-parent"))

        # --- tools match the needs
        text = blob(bp)
        offline = bool(NO_WEB.search(s(needs.get("sources"))))
        web_workers = [a for a in agents if a.kind != "manager" and not a.children and any(t in a.tools for t in WEB_TOOLS)]
        if WEB_STRONG.search(text) and not offline:
            if not web_workers:
                issues.append(Issue("error", "needs.sources", "the deliverable needs web sources/URLs but no worker has web_search/web_fetch; use the researcher template (or add tools: [web_search, web_fetch])", "web-tools"))
            elif not any(all(t in a.tools for t in WEB_TOOLS) for a in web_workers):
                issues.append(Issue("warning", "agents", "web research without both web_search and web_fetch: search finds pages, fetch reads them; grant both", "web-tools-partial"))
            if review_required(needs) and agents and not any(a.kind == "verifier" and any(t in a.tools for t in WEB_TOOLS) for a in agents):
                issues.append(Issue("warning", "agents", "claims are cited from the web but no verifier has web access to re-check them; use the fact-checker template", "verifier-web"))
        elif WEB_WEAK.search(text) and not web_workers and not offline and not is_code(bp):
            issues.append(Issue("warning", "needs.sources", "the text mentions current facts (latest/current/prices/releases) but no agent has web access; confirm that offline work is intended or add a researcher", "web-current"))
        if is_code(bp):
            if not any(has_ws_tools(a) and a.workspace and a.kind != "manager" and not a.children for a in agents):
                issues.append(Issue("error", "agents", "a code goal needs an agent with write and shell tools and a workspace (use the engineer template and set needs.workspace)", "code-tools"))
            code = mapping_or_empty(needs.get("code"))
            for key, what in (("tests", "test runner and what must be tested (e.g. pytest, tests for each criterion)"),
                              ("packaging", "packaging/toolchain (e.g. uv + pyproject)"),
                              ("commits", "commit policy (e.g. commit locally per feature, never push)")):
                if not s(code.get(key)):
                    issues.append(Issue("warning", f"needs.code.{key}", f"not decided: {what}", "code-needs"))
            for where_c, cs in [("task.acceptance", crit if plain else []), *((f"services[{s(x.get('name'))}].acceptance", svc_criteria(x)) for x in services)]:
                if cs and not any(re.search(r"\btests?\b|pytest", c, re.I) for c in cs):
                    issues.append(Issue("warning", where_c, "a code goal has no criterion about tests; add one (which command runs them, that they pass)", "code-criteria"))

        # --- review step
        review = review_required(needs)
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
        for where_c, cs in [("task.acceptance", crit if plain else []), *((f"services[{s(x.get('name'))}].acceptance", svc_criteria(x)) for x in services)]:
            for n, c in enumerate(cs, 1):
                hit = edits_others_files(c)
                if hit and vwords and vwords.search(c):
                    issues.append(Issue("error", f"{where_c}[{n}]", f"'{hit}': a reviewer cannot change another agent's file; say that the reviewer reports findings and the author applies them", "edits-others"))

        # --- budget (the user's cap is for ONE request: the one task, or each request of a service)
        est: Estimate = self._budgets.estimate(agents) if agents else {"total": 0, "per": {}}
        raw_cap = needs.get("budget_runs")
        cap: int | None = None
        total = self._budgets.planned_total(bp, est["total"]) if agents else 0
        if raw_cap is None:
            issues.append(Issue("warning", "needs.budget_runs", f"no budget cap from the user; the estimate is {est['total']} runs: ask what they are willing to spend", "budget"))
        elif not isinstance(raw_cap, int) or isinstance(raw_cap, bool) or raw_cap < 1:
            issues.append(Issue("error", "needs.budget_runs", "budget_runs must be a whole number of runs >= 1", "budget"))
        else:
            cap = raw_cap
        if plain:
            task_runs = task.get("budget")
            if agents and isinstance(task_runs, int) and not isinstance(task_runs, bool):
                total = task_runs
            if cap is not None and total > cap:
                issues.append(Issue("error", "task.budget", f"planned budget {total} runs is above the user's cap of {cap}; lower task.budget or shrink the team", "budget-cap"))
            if agents and total < est["total"]:
                issues.append(Issue("error", "task.budget" if task.get("budget") else "needs.budget_runs", f"{total} runs cannot cover the pipeline: the estimate with one review and one rework cycle is {est['total']} (see estimate()); raise the budget or drop a role", "budget-low"))
            elif agents and total < math.ceil(est["total"] * TIGHT):
                issues.append(Issue("warning", "task.budget", f"{total} runs leaves almost no slack over the estimate of {est['total']}; expect a stall on the first surprise", "budget-tight"))
        self._services.check(bp, agents, tops, cap, est["total"], org, roots, issues)

        # --- models
        pol = s(needs.get("model_policy"))
        if not pol:
            # the default is one model for every agent (nothing to decide); only a team on different models needs a stated policy
            if len({a.model for a in agents}) > 1:
                issues.append(Issue("warning", "needs.model_policy", "the agents run on different models but no model policy says why: state it (for example cheap drafting + strong review)", "model-policy"))
        elif TIERED.search(pol) and not re.match(r"\s*(?:single|same|one|default)\b", pol, re.I) and len(agents) > 1:
            if len({a.model for a in agents}) < 2:
                issues.append(Issue("error", "agents", f"model policy '{pol}' asks for different models for drafting and review, but all agents use the same one; set needs.models {{cheap, strong}} (and give reviewers model: strong)", "model-single"))
            else:
                weak = [a for a in verifiers if authors and {a.model} == {x.model for x in authors}]
                if weak:
                    issues.append(Issue("warning", weak[0].where, "the reviewer uses the same model as the author it checks; the policy asks for a stronger reviewer (model: strong)", "model-review"))

        # --- the lead decides how every other run is spent: it belongs on the strong model (studies A3/A4)
        mdl = mapping_or_empty(needs.get("models"))
        dflt = config_default_model(cfg)
        cheap_id, strong_id = s(mdl.get("cheap")) or dflt, s(mdl.get("strong")) or dflt  # a tier without an id is the org default
        drafters = {x.model for x in agents if x.kind == "author" and not x.children and x.model}
        for a in agents:
            if cheap_id == strong_id or (a.kind != "manager" and not a.children):
                continue  # one model for both tiers: there is no cheaper model to be on
            if a.model == strong_id:
                continue
            on_cheap = a.tier == "cheap" or a.model == cheap_id
            shared = bool(a.model and a.model in drafters)
            if on_cheap or shared:
                why = "the cheap model" if on_cheap else f"{a.model}, the same model as the drafters, while a strong model ({strong_id}) is available"
                issues.append(Issue("warning", a.where, f"{a.addr} directs the team but runs on {why}; the lead decides how every other run is spent; cheap leads misroute rework and waste runs (studies A3/A4). Give it model: strong", "manager-cheap-model"))

        # --- elicited preferences the org itself does not use but the assistant must honor
        for key, hint in (("scope", "what is in and out of scope"), ("approval", "when the user wants to approve (plan, before start, final)"),
                          ("progress", "how the user wants progress updates")):
            if not s(needs.get(key)):
                issues.append(Issue("warning", f"needs.{key}", f"not elicited: {hint}", f"needs-{key}"))
        return issues
