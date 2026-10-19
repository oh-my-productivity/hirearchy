# mypy: ignore-errors
"""Blueprints: a whole organization for one goal as a reviewable document.

A blueprint is a plain dict (YAML or JSON)::

    mission: one paragraph
    needs:                      # the elicited requirements, in the user's terms
      scope: ...
      deliverable: {description, format, max_words, path}
      quality_bar: ...  sources: ...  workspace: /abs/path  budget_runs: 25
      inputs: [/abs/read-only/folder]   # read-only sources for the agents (kiro enforces: they cannot write there)
      models: {cheap: <model id>, strong: <model id>}   model_policy: ...   # optional: no models = every agent on the org default (claude-sonnet-5.5)
      review: true|false|text   approval: ...   progress: ...
      kind: research|writing|code    code: {tests, packaging, commits}
    agents:                     # exactly one top-level agent (budget flows down from it)
      - {name, role, template, charter, model, tools, workspace, inputs, can_hire, max_children, scale, children: [...]}
    task: {to, title, goal, acceptance: [exact, checkable items], inputs: [...], budget}
    services:                   # optional: standing tasks the top-level agent offers (see ``orgmcp.services``)
      - {name, owner, description, inputs: [{name, description, required}], acceptance: [...],
         deliverable: {description, format, max_words, path}, budget, playbook, locked}
    # with services, ``task`` is optional; it may be a first request: {service, inputs: {...}, title, note}

``validate`` encodes what went wrong in the usability studies as checks (errors block ``apply``, warnings are
shown in the plan), ``render_plan`` produces the text the user approves, ``apply`` builds the organization.

THE BOUNDARY BETWEEN THE TWO HALVES (steps C-blueprint-1 and C-blueprint-2). The first half of the old module - the role library, loading, the
agents, ``validate`` and its rules, the access report, the budget estimate - is classes behind the interfaces of ``api`` (``_loader``, ``_resolver``,
``_validator``, ...); the functions of that half are here as ADAPTERS (below: they build the classes over the parts that ``orgmcp.app`` installed
and over the ``Org`` they are given) or as aliases of the pure functions, and keep their old names for the callers and tests that still use them
(``LEGACY_EXPORTS``). THE SECOND HALF IS STILL THE OLD CODE, verbatim, for C-blueprint-2 to move: ``_charter``, ``default_playbook``, ``_tree_lines``,
``render_plan``, the ``PLAN_*`` texts and ``plan_for_user`` with its helpers, ``plan_id``, ``propose_text``, ``propose``, ``Summary`` and ``apply``.
It reaches the first half only through the private aliases and adapters of the next section (``_s``, ``_needs``, ``_resolve``, ``estimate``, ...);
when that half has moved, so does that section.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import services as services_mod
from ..kernel import ROOT, OrgError
from ..kernel import depth as org_depth
from ..settings import DEFAULT_MODEL
from ._assembly import assembly_of
from ._budgeting import KINDS as KINDS
from ._budgeting import REWORK_RUNS as REWORK_RUNS
from ._budgeting import SLACK as SLACK
from ._budgeting import TIGHT as TIGHT
from ._host import OrgFacts as Org  # the legacy functions are duck-typed (a feature may not import the facade); step C-blueprint-2 names what ``apply`` needs
from ._loader import normalize as _normalize
from ._resolver import declared_inputs as declared_inputs
from ._resolver import review_roots as review_roots
from ._rules import blob as _blob
from ._rules import delivers_directly as _delivers_directly
from ._rules import edits_others_files as edits_others_files
from ._rules import is_code as _is_code
from ._rules import review_required as _review_required
from ._text import CLIP as CLIP
from ._text import GOAL_CLIP as GOAL_CLIP
from ._text import clip as _clip
from ._view import AGENT_KEYS as AGENT_KEYS
from ._view import NEEDS_KEYS as NEEDS_KEYS
from ._view import REQUEST_KEYS as REQUEST_KEYS
from ._view import SERVICE_KEYS as SERVICE_KEYS
from ._view import TASK_KEYS as TASK_KEYS
from ._view import WEB_TOOLS as WEB_TOOLS
from ._view import WRITE_TOOLS as WRITE_TOOLS
from ._view import criteria_of as _criteria
from ._view import deliverable_of as _deliverable
from ._view import has_plain_task as _has_plain_task
from ._view import is_plain as _plain
from ._view import is_request as _is_request
from ._view import items as _list
from ._view import needs_of as _needs
from ._view import s as _s
from ._view import services_of as _services
from ._view import svc_criteria as _svc_criteria
from ._view import svc_deliverable as _svc_deliverable
from .api import Agent, BlueprintError, Issue, Role, errors

ROLES_DIR = Path(__file__).parent.parent / "roles"  # where the flat module had them (``test_wire_blueprint`` pins it to the one the wiring finds)



# ------------------------------------------------------------------------------ the first half: adapters over the classes of the package
# Each builds the classes over the parts that ``orgmcp.app`` installed (``assembly_of``) and, when it is given one, over the ``Org``.


def role_names() -> list[str]:
    return assembly_of(None).roles.role_names()


def get_role(name: str) -> Role | None:
    return assembly_of(None).roles.get_role(name)


def load(source):
    """A blueprint from a path (``Path`` or an existing file name) or from YAML/JSON text."""
    return assembly_of(None).loader.load(source)


def load_text(text: str) -> dict:
    """A blueprint from YAML/JSON text only. Never reads a file, whatever the text looks like (for text from a tool call)."""
    return assembly_of(None).loader.load_text(text)


def _resolve(bp: dict, org: Org | None, roots: list[Path], issues: list[Issue]) -> list[Agent]:
    a = assembly_of(org)
    return a.resolver.resolve(bp, a.org, roots, issues)


def validate(bp: dict, *, org: Org | None = None, allowed_roots: list | None = None) -> list[Issue]:
    """All problems with a blueprint. Errors block ``apply``; warnings are shown in the plan.

    ``org`` supplies the limits (``max_depth``) and the names already taken; ``allowed_roots`` the directories
    agents' workspaces and the deliverable path may be in (default: home, temp dir and the current directory, or
    ``$ORGMCP_WORKSPACE_ROOTS``).
    """
    return assembly_of(org).validator.validate(bp, org_exists=org is not None, allowed_roots=allowed_roots)


def org_files_readable(a: Agent) -> bool:
    """Can this agent open files in the organization (its own and its teammates' ``work/``) with the tools it holds?"""
    return assembly_of(None).access.org_files_readable(a)


def access_facts(a: Agent) -> dict:
    """What the runtime lets this agent reach with kiro's file tools: the ONE computation behind both the technical ``Access:`` line and the plain-words one."""
    return dict(assembly_of(None).access.facts(a))


def _access(a: Agent) -> str:
    """One line on what the runtime lets this agent reach with kiro's file tools (and what it only instructs)."""
    return assembly_of(None).access.line(a)


def estimate(agents: list[Agent]) -> dict:
    """Runs one pass plus one rework cycle needs. The model behind the budget check and the budget split."""
    return dict(assembly_of(None).budgets.estimate(agents))


def planned_total(bp: dict, est_total: int) -> int:
    return assembly_of(None).budgets.planned_total(bp, est_total)


def budget_split(agents: list[Agent], total: int) -> dict[str, dict]:
    """addr -> {grant, keeps}: what the parent hands down at first, and what the agent keeps for itself."""
    return {addr: dict(split) for addr, split in assembly_of(None).budgets.budget_split(agents, total).items()}


def service_budget(s: dict, est_total: int, cap: int | None) -> int:
    """Runs handed down with each request of service ``s``: its own ``budget``, else the estimate plus slack within the cap."""
    return assembly_of(None).budgets.service_budget(s, est_total, cap)


def _svc_budgets(bp: dict, agents: list[Agent]) -> dict[str, int]:
    return assembly_of(None).budgets.service_budgets(bp, agents)


# ------------------------------------------------------------------------------------------------ the second half: the old code, for C-blueprint-2


def _charter(a: Agent, agents: list[Agent], bp: dict, split: dict[str, dict]) -> str:
    by = {x.addr: x for x in agents}
    needs, d = _needs(bp), _deliverable(bp)
    offers = [_s(x.get("name")) for x in _services(bp)] if a.parent is None else []
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
            asg.append(f"- {c}: {k.role} ({k.kind}; tools: {', '.join(k.tools) or 'none'}; model: {k.model})")
        grants = [(c, split[c]["grant"]) for c in a.children]
        if offers and not _has_plain_task(bp):
            asg.append("Budget plan: each request arrives with the budget of its service, and its split between you and your team is in the playbook (`## Budget plan`). "
                       "Hand down no more than that plan says, with `budget=` set explicitly; keep the reserve for one review and rework cycle. "
                       "Runs you do not spend return to your parent automatically with your final report.")
        else:
            asg.append(
                f"Budget plan: you start with {split[a.addr]['grant']} runs. Initial grants, set explicitly with `budget=`: "
                + ", ".join(f"{c} {n}" for c, n in grants) + f". Each grant already includes that worker's one rework (author) or re-check (verifier) run. You keep {split[a.addr]['keeps']} runs: your own runs plus the reserve for "
                "one review and one rework cycle (rework tasks hand down 1-2 runs each). Do not hand down more than this up front. Runs you do not spend return to your parent automatically with your final report.")
        vs = [c for c in a.children if by[c].kind == "verifier"]
        if vs:
            au = [c for c in a.children if by[c].kind == "author"]
            asg.append(f"Review loop: {', '.join(au) or 'the authors'} produce; {', '.join(vs)} verif{'ies' if len(vs) == 1 else 'y'} independently and report findings and required changes to you; "
                       "you send them to the author with `revises`; verifiers never edit the author's file.")
    if offers:
        asg.append(
            f"Services you offer: {', '.join(offers)} (the runtime shows them, with their contract, in your prompt). A task with a `service:` "
            "header is a request for one: for it the playbook shown in your prompt is the procedure (steps, who does what, budget plan), "
            "and wherever this charter's general procedure differs, the playbook wins. You own the playbook and improve it with `revise_playbook` "
            "from the evidence shown before a new request. The acceptance criteria come from the request and the contract; improving the playbook "
            "may raise the bar, never lower it.")
    parts.append("\n".join(asg))
    if a.extra:
        parts.append(("## Additional instructions\n" if a.template else "") + a.extra)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------------------- default playbook


def default_playbook(owner: Agent, agents: list[Agent], service: dict, budget: int) -> str:
    """Playbook v1 of a service when the blueprint gives none: the lead charter's procedure for THIS team, as steps.

    Built from the same facts as ``_charter`` and the manager template: who produces, who verifies, the sequencing
    (a step is delegated when its inputs exist), author-routed rework with ``revises``, the runs held back for one
    rework cycle, the final check of every criterion and the report with ``lessons``. The owner improves it later.
    """
    by = {x.addr: x for x in agents}
    split = budget_split(agents, budget)
    est = estimate(agents)["per"]
    kids = [by[c] for c in owner.children]
    makers = [k for k in kids if k.kind != "verifier"]
    checkers = [k for k in kids if k.kind == "verifier"]
    path = _s(_svc_deliverable(service).get("path"))
    grant = lambda k: split[k.addr]["grant"]  # noqa: E731
    steps = ["Read the request in your prompt: its inputs, every acceptance criterion and the deliverable. The criteria come from the contract "
             "and can only be met, never changed; copy the relevant ones verbatim into every task you delegate."]
    if not kids:
        steps.append("Do the work yourself, following the request's deliverable and criteria exactly.")
    for i, k in enumerate(makers):
        what = f"`{k.name}` ({k.role})"
        if i == 0:
            steps.append(f"Delegate to {what} with `budget={grant(k)}`: its part of the request, with the criteria it must meet. On this first run delegate only the steps that need nothing from a teammate.")
        else:
            steps.append(f"When the previous result is in, read its artifact yourself, then delegate to {what} with `budget={grant(k)}`, naming the artifact it builds on. "
                         "Never delegate a step before its inputs exist, and send no status messages: results wake you.")
    for k in checkers:
        steps.append(f"When the work exists, delegate to `{k.name}` ({k.role}) with `budget={grant(k)}` to check the final file independently against every criterion. "
                     "It reports findings and required changes to you and never edits the author's file.")
    if checkers:
        usual = f"; for the deliverable usually `{makers[-1].name}`" if makers else ""
        steps.append("If a check fails: send the required changes, quoted verbatim, to the AUTHOR of the failing file "
                     f"(`delegate(to=<author>, revises=<that author's task id>, budget=1)`{usual}), then have the checker re-check that same file "
                     "(`delegate(to=<checker>, revises=<the checker's task id>)`). One rework and one re-check; if it still fails, report `blocked` with options "
                     "and the checker's final line instead of starting another cycle.")
    steps.append("Read the final artifact yourself and check it against EVERY criterion of the request, quoting counts from your own `read` output"
                 + (", and paste the checker's final coverage line verbatim." if checkers else "."))
    steps.append("Report: `done` only if every criterion is met (else `blocked` with the deviation and a recommended decision). Name the deliverable's path"
                 + (f" (the assistant copies it to {path})" if path else "")
                 + " and pass `lessons`: 1-3 lines for the next request - what worked, what to change in this playbook, and the evidence (runs used, rework, review findings).")
    budget_lines = [f"Request budget: {budget} runs (the contract's). Hand down no more than this up front, each with `budget=` set explicitly:"]
    for k in kids:
        e = est[k.addr]
        budget_lines.append(f"- {k.name}: {grant(k)} runs ({e['pass']} work + {e['rework']} rework or re-check" + (", plus its team" if k.children else "") + ")")
    own = est[owner.addr]["total"]
    keeps = split[owner.addr]["keeps"]
    budget_lines.append(f"- you ({owner.name}): keep {keeps} runs: your own {own} (plan, process each result, final check, report, one rework cycle)"
                        + (f" and {keeps - own} of slack" if keeps - own > 0 else "") + ".")
    budget_lines.append("Unspent runs return to your parent with your final report.")
    text = ("## Steps\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(steps, 1))
            + "\n\n## Budget plan\n" + "\n".join(budget_lines)
            + "\n\n## Pitfalls\nnone yet: add them from lessons and feedback")
    return text


# ----------------------------------------------------------------------------------------------- plan


def _tree_lines(agents: list[Agent]) -> list[str]:
    by = {a.addr: a for a in agents}
    out: list[str] = []

    def line(a: Agent, indent: int) -> None:
        tpl = f"[{a.template.name}]" if a.template else "[custom]"
        ws = f" ws={a.workspace}" if a.workspace else ""
        out.append(f"{'  ' * indent}- {a.name} {tpl} {a.role}: model={a.model}, tools={','.join(a.tools) or 'none'}{ws}")
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
    roots = assembly_of(org).roots.roots(allowed_roots)
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
    need("Deliverable", (_s(d.get("description")) + (f" [{spec}]" if spec else "")) if d.get("description")
         else ("per service (see Services below)" if not _plain(bp) else ""))
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
    plain = _plain(bp)
    total = planned_total(bp, est["total"]) if agents else 0
    if isinstance(task.get("budget"), int) and plain:
        total = task["budget"]
    cap = needs.get("budget_runs")
    svc_budgets = _svc_budgets(bp, agents)

    def split_lines(total: int, indent: str = "  ") -> None:
        split = budget_split(agents, total)
        for a in agents:
            e = est["per"][a.addr]
            if a.children:
                keeps = split[a.addr]["keeps"]
                L.append(f"{indent}{a.addr}: starts with {split[a.addr]['grant']}, hands down "
                         + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                         + f" (each includes its rework/re-check run), keeps {keeps} (own {e['total']}"
                         + (f" + slack {keeps - e['total']})" if keeps - e["total"] else ")"))
            else:
                L.append(f"{indent}{a.addr}: {split[a.addr]['grant']} runs ({e['pass']} work + {e['rework']} rework)")

    if plain:
        L += ["", f"Budget: {total} runs planned" + (f" (your cap: {cap})" if cap else " (no cap given)")
              + f", estimate {est['total']} for one pass + one review/rework cycle:",
              "  This is a ceiling: runs the team does not spend come back automatically, agent by agent, with their final reports, until what is left returns to you."]
        if agents:
            split_lines(total)
    else:
        L += ["", "Budget per request" + (f" (your cap: {cap})" if cap else " (no cap given)") + f", estimate {est['total']} for one pass + one review/rework cycle:",
              "  A ceiling: runs the team does not spend come back automatically with the final report of each request."]
        for name, n in svc_budgets.items():
            L.append(f"  service {name}: {n} runs per request")
            if agents:
                split_lines(n, "    ")

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
    L.append(f"- {_s(d.get('description')) or ('per service (see Services below)' if not plain else '(missing)')}" + (f" ({spec})" if spec else ""))
    if _s(d.get("path")):
        copy = any(i.code == "path-delivery" and i.path.startswith("needs.") for i in issues)
        L.append(f"- Final location: {_s(d['path'])}" + (" (copied there by the assistant after verification)" if copy else " (written there by the team)"))
    elif plain or d.get("description"):
        L.append("- Final location: inside the organization (no path given)")

    if plain:
        L += ["", f"First task: to {_s(task.get('to')) or (agents[0].addr if agents else '?')}: {_s(task.get('title')) or '(missing)'}"]
        crit = _criteria(bp)
        L += [f"  {i}. {c}" for i, c in enumerate(crit, 1)] or ["  (no acceptance criteria)"]
    if _services(bp):
        L += ["", f"Services ({len(_services(bp))}), offered by {agents[0].addr if agents else '?'} and defined by root (the contract: only root can change it):"]
        for sv in _services(bp):
            name = _s(sv.get("name"))
            sd = _svc_deliverable(sv)
            ssp = ", ".join(x for x in (_s(sd.get("format")), f"max {sd['max_words']} words" if sd.get("max_words") else "") if x)
            L += [f"- {name}: {_s(sv.get('description')) or '(missing)'}", f"  inputs: {_input_words(sv)}",
                  f"  budget: {svc_budgets.get(name, 0)} runs per request" + (", locked (the lead may not revise the playbook)" if sv.get("locked") is True else ""),
                  f"  deliverable: {_s(sd.get('description')) or '(missing)'}" + (f" [{ssp}]" if ssp else "") + f"; delivered to: {_svc_delivery(sv, agents, bp)}",
                  "  acceptance (the contract, travels with every request):"]
            L += [f"    {i}. {c}" for i, c in enumerate(_svc_criteria(sv), 1)] or ["    (none)"]
            pb = sv.get("playbook")
            L.append("  playbook v1: " + (f"given in the blueprint ({len(pb.split())} words)" if isinstance(pb, str) and pb.strip() else "generated from the team (steps, budget plan, pitfalls):"))
            if not (isinstance(pb, str) and pb.strip()) and agents:
                L += ["    " + ln for ln in default_playbook(agents[0], agents, sv, svc_budgets.get(name, 0)).splitlines()]
        L.append(_reflection_line(agents[0].name if agents else "lead"))
        if _is_request(bp):
            L.append(f"First request: service {_s(task.get('service'))}" + (f": {_request_words(bp)}" if _request_words(bp) else "") + (f"; title: {_s(task.get('title'))}" if _s(task.get("title")) else ""))
        elif not plain:
            L.append("No first task: nothing runs until you ask for a request (request(service, inputs), then start()).")

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

PLAN_HEADING = "PLAN FOR YOU"  # the first line of the block the user sees: no instruction inside the block
PLAN_DRAFT_HEADING = "DRAFT - NOT READY (it has errors: fix the blueprint and propose again; do not show this to the user)"
PLAN_END = "--- machine marker: the user block ends above; do not show this line or anything below it ---"
PLAN_SHOW = ("Show the block below to the user exactly as written, from its first line up to (not including) the marker line; "
             "one plain-words intro line before it is fine.")
TOOL_WORDS = {"read": "read files", "write": "write files", "shell": "run commands", "web_search": "search the web",
              "web_fetch": "read web pages"}
SHOWN_CRITERIA = 8  # the block stays compact (about 40 lines); the full lists are in the details
SHOWN_WARNINGS = 5
HIDDEN_WARNINGS = {"path-delivery", "path-parent", "needs-scope", "needs-approval", "needs-progress"}  # said elsewhere in the block
PLAN_ID_LENGTH = 12
SHOWN_SERVICE_CRITERIA = 5  # per service in the block; the details have them all


def plan_id(bp: dict) -> str:
    """A short stable hash of the normalized blueprint: the same blueprint (whatever its YAML layout, comments or
    key order) always gives the same id; any change to a value gives another. ``apply_org`` requires it, so what is
    applied is what ``propose_org`` showed. Stateless: nothing is stored, it survives restarts."""
    canon = json.dumps(_normalize(bp), sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:PLAN_ID_LENGTH]


def _agent_access(a: Agent) -> str:
    """What the agent may touch, in plain words: the same facts as the ``Access:`` line (``access_facts``)."""
    f = access_facts(a)
    ws, bits = a.workspace, []
    if f["web"]:
        bits.append("can " + " and ".join(TOOL_WORDS[t] for t in f["web"]))
    if f["read"][0]:
        bases = f["read"][1]
        ins = f["inputs"]
        org = " and the organization's own files" if f["org"] else ""
        if f["write"][0] and ws:
            bits.append("can read files in " + ", ".join(bases) + (f" ({', '.join(ins)} read-only)" if ins else "") + org)
        elif bases:
            bits.append("can read files only in " + ", ".join(bases) + org)
        else:
            bits.append("can read no files outside the organization")
    elif f["inputs_via_orgmcp"]:
        bits.append("can read " + ", ".join(f["inputs"]) + " through the organization's read tool")
    if f["write"][0]:
        bits.append(f"changes files only in {ws}" if ws else "changes no files (no workspace)")
    if f["shell"][0]:
        bits.append("can run commands, which are NOT confined: it is told to stay in "
                    + (str(ws) if ws else "its own folder") + ", but nothing enforces that")
    if not f["write"][0] and not f["shell"][0]:
        bits.append("cannot change your files")
    lead = "directs the team; does not produce the work itself" if (a.kind == "manager" or a.children) else ""
    text = "; ".join(bits)
    return f"{lead}; {text}" if lead and text and text != "cannot change your files" else (lead or text)


def _user_tree(agents: list[Agent]) -> list[str]:
    by = {a.addr: a for a in agents}
    out: list[str] = []

    def line(a: Agent, indent: int) -> None:
        out.append(f"{'  ' * indent}- {a.name} ({a.role}, model {a.model}): {_agent_access(a)}")
        for c in a.children:
            line(by[c], indent + 1)

    for a in agents:
        if a.parent is None:
            line(a, 0)
    return out


def _user_budget(agents: list[Agent], bp: dict) -> list[str]:
    needs, task = _needs(bp), bp.get("task") if isinstance(bp.get("task"), dict) else {}
    est = estimate(agents) if agents else {"total": 0, "per": {}}
    cap = needs.get("budget_runs")
    if not _plain(bp):  # services only: the budget is per request
        budgets = _svc_budgets(bp, agents)
        top = max(budgets.values(), default=0)
        out = [f"Budget: up to {top} runs per request (one run = one working session of one agent), "
               + (f"your cap per request is {cap}" if cap else "you gave no cap") + f"; the minimum for one review and rework is {est['total']}. "
               "Unspent runs come back to you."]
        if agents and len(budgets) == 1:
            split = budget_split(agents, top)
            for a in agents:
                if a.children:
                    out.append(f"  {a.addr} starts with {split[a.addr]['grant']}, hands down "
                               + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                               + f" and keeps {split[a.addr]['keeps']} for planning, checking and rework.")
        if agents:
            out.append("If a check still fails after one rework, I'll come back to you with options before spending the reserve; "
                       "nothing beyond a request's budget is spent without your OK.")
        return out
    total = planned_total(bp, est["total"]) if agents else 0
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
        out.append(_failure_policy(total, est["total"]))
    return out


def _failure_policy(total: int, minimum: int) -> str:
    """What happens when the check fails again after the one rework the budget is built for, with the reserve in runs.

    ``minimum`` = runs for one pass plus one rework cycle; what the plan holds above it is the reserve.
    """
    reserve = max(0, total - minimum)
    head = "If the check still fails after one rework, I'll come back to you with options"
    if reserve:
        return (f"{head} before spending the reserve (about {reserve} runs); nothing beyond the {total} planned "
                "runs is spent without your OK.")
    return f"{head}; the plan has no reserve beyond that rework, and nothing beyond the {total} planned runs is spent without your OK."


def _input_words(sv: dict) -> str:
    try:
        ins = services_mod._inputs(sv.get("inputs"))
    except OrgError:
        return "(see the errors)"
    return ", ".join(f"{i['name']} ({'required' if i['required'] else 'optional'})" for i in ins) or "nothing: every request is the same"


def _svc_delivery(sv: dict, agents: list[Agent], bp: dict) -> str:
    path = _s(_svc_deliverable(sv).get("path"))
    if not path:
        ws = _s(_needs(bp).get("workspace"))
        if ws and _is_code(bp):
            return f"the workspace {ws} (the team works and commits there)"
        return "inside the organization folder (no location given)"
    p = Path(os.path.expanduser(path))
    direct = p.is_absolute() and _delivers_directly(agents, p.resolve())
    return f"{path} " + ("(the team writes it there)" if direct else "(I copy each result there after checking it)")


def _request_words(bp: dict) -> str:
    t = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    ins = t.get("inputs") if isinstance(t.get("inputs"), dict) else {}
    return ", ".join(f"{k}: {_clip(v, 80)}" for k, v in ins.items() if _s(v))


def _reflection_line(owner: str) -> str:
    who = "the lead" if owner == "lead" else f"the lead ({owner})"
    return (f"After each request {who} records lessons; before the next one it reviews them with your feedback and may improve how the team "
            "works (its playbook). It cannot change these checks: only you can, through me.")


def _user_services(bp: dict, agents: list[Agent]) -> list[str]:
    """The compact Services part of the plan for the user: per service what it is, what you provide, its budget,
    its checks (the contract, first few in full), where it is delivered; then the reflection rule and what runs now."""
    svcs = _services(bp)
    if not svcs:
        return []
    budgets = _svc_budgets(bp, agents)
    top = next((a for a in agents if a.parent is None), None)
    out = ["Services (kept ready, requested whenever you want):"]
    for sv in svcs:
        name = _s(sv.get("name"))
        crit = _svc_criteria(sv)
        out.append(f"- {name}: {_clip(sv.get('description'), 200) or '(missing)'}")
        out.append(f"  You provide: {_input_words(sv)}")
        out.append(f"  Each request: up to {budgets[name]} runs")
        out.append("  Checks:" if crit else "  Checks: (none given)")
        out += [f"    {i}. {' '.join(c.split())}" for i, c in enumerate(crit[:SHOWN_SERVICE_CRITERIA], 1)]
        if len(crit) > SHOWN_SERVICE_CRITERIA:
            out.append(f"    ... and {len(crit) - SHOWN_SERVICE_CRITERIA} more (see the details)")
        out.append(f"  Delivered to: {_svc_delivery(sv, agents, bp)}")
    out.append(_reflection_line(top.name if top else "the lead"))
    if _is_request(bp):
        out.append(f"First request, started on approval: {_s(bp['task'].get('service'))}" + (f" ({_request_words(bp)})" if _request_words(bp) else "") + ".")
    elif not _has_plain_task(bp):
        out.append("Nothing runs until you ask for a request: approving only creates the team and the services.")
    return out


def _models_line(agents: list[Agent], needs: dict) -> str:
    """The plan's Models line: what the agents will really run on (the resolved ids), plus the stated policy if they differ."""
    used: dict[str, int] = {}
    for a in agents:
        used[a.model] = used.get(a.model, 0) + 1
    if not used:
        return f"{DEFAULT_MODEL} (no agents yet)"
    if len(used) == 1:
        return f"{next(iter(used))} for every agent"
    parts = ", ".join(f"{m} for {n} agent{'s' if n != 1 else ''}" for m, n in used.items())
    pol = _clip(needs.get("model_policy")).rstrip(".")
    return f"{parts}" + (f" ({pol})" if pol else "")


def plan_for_user(bp: dict, issues: list[Issue] | None = None, *, org: Org | None = None, allowed_roots: list | None = None) -> str:
    """The compact, plain-language plan the assistant shows to the user verbatim (about 40 lines at most).

    Goal, needs as understood, the team (role, model, tools, access), budget and its split, review, deliverable and
    where it will be delivered, the success checks, checkpoints and warnings. ``render_plan`` has the full details.
    """
    if issues is None:
        issues = validate(bp, org=org, allowed_roots=allowed_roots)
    roots = assembly_of(org).roots.roots(allowed_roots)
    agents = _resolve(bp, org, roots, [])
    needs, d = _needs(bp), _deliverable(bp)
    task = bp.get("task") if isinstance(bp.get("task"), dict) else {}
    errs = [i for i in issues if i.level == "error"]
    warns = [i for i in issues if i.level == "warning" and i.code not in HIDDEN_WARNINGS]
    plain = _plain(bp)
    L: list[str] = [PLAN_DRAFT_HEADING if errs else PLAN_HEADING, f"Goal: {_clip(bp.get('mission'), GOAL_CLIP) or '(missing)'}", "What I understood you need:"]

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
    L.append(f"- Models: {_models_line(agents, needs)}")

    L.append(f"Team ({len(agents)} agents):")
    L += _user_tree(agents) or ["- (none)"]
    L += _user_budget(agents, bp)

    verifiers = [a for a in agents if a.kind == "verifier"]
    r = _review_required(needs)
    if verifiers:
        L.append("Checking: " + ", ".join(v.name for v in verifiers) + " review"
                 + ("s" if len(verifiers) == 1 else "") + " the work independently (they did not write it); required changes go back "
                 f"to the author. I then re-check the final result against every {'success check' if plain else 'service check'} below.")
    else:
        L.append("Checking: no independent reviewer" + (" (you did not ask for one)" if r is False else " (!)")
                 + f". I still re-check the final result against every {'success check' if plain else 'service check'} below.")

    spec = ", ".join(x for x in (_s(d.get("format")), f"max {d['max_words']} words" if d.get("max_words") else "") if x)
    if plain or d.get("description"):
        L.append(f"Deliverable: {_clip(d.get('description')) or '(missing)'}" + (f" [{spec}]" if spec else ""))
        if _s(d.get("path")):
            copied = any(i.code == "path-delivery" and i.path.startswith("needs.") for i in issues)
            L.append(f"  Delivered to: {_s(d['path'])}" + (" (I copy it there after checking it)" if copied else " (the team writes it there)"))
        elif _s(needs.get("workspace")) and _is_code(bp):
            L.append(f"  Delivered to: the workspace {_s(needs['workspace'])} (the team works and commits there)")
        else:
            L.append("  Delivered to: inside the organization folder (no location given)")

    if plain:
        crit = _criteria(bp)
        L.append("Done when ALL of these hold:" if crit else "Done when: (no success checks given)")
        L += [f"  {i}. {' '.join(_s(c).split())}" for i, c in enumerate(crit[:SHOWN_CRITERIA], 1)]  # the contract: in full
        if len(crit) > SHOWN_CRITERIA:
            L.append(f"  ... and {len(crit) - SHOWN_CRITERIA} more (see the details)")
    L += _user_services(bp, agents)

    L.append(f"Checkpoints: approval - {_clip(needs.get('approval')).rstrip('.') or 'this plan, before anything is built or started'}; "
             f"progress - {_clip(needs.get('progress')).rstrip('.') or 'one line when you ask'}; any spend beyond the budget needs your OK.")
    if warns:
        L.append(f"Warnings ({len(warns)}):")
        L += [f"- {_clip(w.message)}" for w in warns[:SHOWN_WARNINGS]]
        if len(warns) > SHOWN_WARNINGS:
            L.append(f"- ... and {len(warns) - SHOWN_WARNINGS} more (see the details)")
    if errs:
        L.append(f"Errors ({len(errs)}):")
        L += [f"- {e.path}: {_clip(e.message)}" for e in errs[:SHOWN_WARNINGS]]
    L.append("Nothing is created or started until you approve. Reply 'approve', or tell me what to change." if not errs
             else "Cannot apply yet.")
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
    show = "" if errors(issues) else PLAN_SHOW
    return "\n\n".join(x for x in (target, show, block, PLAN_END, "Details (the full plan, for you; the user need not read it):\n" + details, nxt) if x)


def propose(source, *, org: Org | None = None, allowed_roots: list | None = None) -> str:
    """Load a blueprint (text, path or dict), validate it and return the plan text. Writes nothing."""
    bp = load(source)
    return render_plan(bp, validate(bp, org=org, allowed_roots=allowed_roots), org=org, allowed_roots=allowed_roots)


# ----------------------------------------------------------------------------------------------- apply


@dataclass
class Summary:
    agents: list[str]
    task_id: str  # "" when the blueprint gave no first task (services only)
    to: str
    budget: int
    warnings: list[Issue] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    service_request: str = ""  # the service the first task requested, if it is a request

    def text(self) -> str:
        lines = [f"created {len(self.agents)} agents: {', '.join(self.agents)}"]
        if self.services:
            lines.append(f"defined {len(self.services)} service(s) of {self.to}: {', '.join(self.services)} (contract and playbook v1)")
        if self.task_id and self.service_request:
            lines.append(f"first request: service {self.service_request}, task {self.task_id} -> {self.to} (budget {self.budget})")
        elif self.task_id:
            lines.append(f"task {self.task_id} -> {self.to} (budget {self.budget})")
        else:
            lines.append("no task was given: the services are ready and nothing runs yet. To use one: request(service, inputs) "
                         "(or `orgmcp request SERVICE --input key=value`), then start()")
        lines += [f"warning: {w.path}: {w.message}" for w in self.warnings]
        return "\n".join(lines)


def apply(org: Org, bp: dict, *, allowed_roots: list | None = None) -> Summary:
    """Create the agents (parents first, as root through each parent), define the services, and give the first task.

    The first task is a plain task, a first request for a service (``task.service``), or none (services only: they
    are ready to be requested). Refuses on any validation error or existing name, before writing anything. If a hire,
    a service definition or the delegation fails midway, everything created is retired again and the error is raised.
    """
    issues = validate(bp, org=org, allowed_roots=allowed_roots)
    errs = errors(issues)
    if errs:
        raise BlueprintError("blueprint has errors, nothing was created:\n" + "\n".join(f"- {i.path}: {i.message}" for i in errs))
    roots = assembly_of(org).roots.roots(allowed_roots)
    agents = _resolve(bp, org, roots, [])
    task = bp["task"] if isinstance(bp.get("task"), dict) else None
    est = estimate(agents)
    total = planned_total(bp, est["total"])
    split = budget_split(agents, total)
    top = agents[0]
    made_dirs: list[Path] = []
    created: list[str] = []
    defined: list[str] = []
    msg = None
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
        budgets = _svc_budgets(bp, agents)
        for sv in _services(bp):
            name = _s(sv.get("name"))
            d = dict(services_mod._deliverable(_svc_deliverable(sv)))
            if d.get("path"):
                d["path"] = os.path.expanduser(d["path"])
            playbook = sv["playbook"].strip() if isinstance(sv.get("playbook"), str) and sv["playbook"].strip() else default_playbook(top, agents, sv, budgets[name])
            org.define_service(
                ROOT, top.addr, name, description=_s(sv.get("description")), inputs=services_mod._inputs(sv.get("inputs")),
                acceptance=_svc_criteria(sv), deliverable=d, budget=budgets[name], playbook=playbook, locked=sv.get("locked") is True,
            )
            defined.append(name)
        if task is not None and "service" in task:
            msg = org.request(ROOT, _s(task["service"]), task.get("inputs") or {}, title=_s(task.get("title")), note=_s(task.get("note")))
        elif task is not None:
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
            if org.exists(addr) and org_depth(addr) == 1:
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
    what = (f"task {msg.id} -> {top.addr}" if msg is not None else "no task") + (f", services: {', '.join(defined)}" if defined else "")
    org.commit(f"root: applied blueprint ({len(created)} agents), {what}")
    return Summary(created, msg.id if msg is not None else "", top.addr, msg.budget if msg is not None else 0,
                   [i for i in issues if i.level == "warning"], defined, _s(task["service"]) if msg is not None and task and "service" in task else "")
