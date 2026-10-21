"""``TextUserPlan``: the compact block the assistant shows to the user."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..settings import DEFAULT_MODEL
from ._plan_texts import (
    HIDDEN_WARNINGS,
    PLAN_DRAFT_HEADING,
    PLAN_HEADING,
    SHOWN_CRITERIA,
    SHOWN_SERVICE_CRITERIA,
    SHOWN_WARNINGS,
)
from ._protocols import AccessWording, BudgetPlanning, PlanBasis, PlanWords, UserPlanning
from ._rules import is_code, review_required
from ._text import GOAL_CLIP, clip
from ._view import (
    criteria_of,
    deliverable_of,
    has_plain_task,
    is_plain,
    is_request,
    items,
    mapping_or_empty,
    needs_of,
    s,
    services_of,
    svc_criteria,
    task_of,
)
from .api import Agent, Issue


class TextUserPlan(UserPlanning):
    def __init__(self, basis: PlanBasis, budgets: BudgetPlanning, access: AccessWording, words: PlanWords) -> None:
        self._basis = basis
        self._budgets = budgets
        self._access = access
        self._words = words

    def render(self, bp: Mapping[str, object], issues: Sequence[Issue] | None, allowed_roots: Sequence[str | Path] | None) -> str:
        """The compact, plain-language plan the assistant shows to the user verbatim (about 40 lines at most).

        Goal, needs as understood, the team (role, model, tools, access), budget and its split, review, deliverable and
        where it will be delivered, the success checks, checkpoints and warnings. ``render_plan`` has the full details.
        """
        if issues is None:
            issues = self._basis.issues(bp, allowed_roots)
        agents = self._basis.agents(bp, allowed_roots)
        needs, d = needs_of(bp), deliverable_of(bp)
        task = task_of(bp)
        errs = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level == "warning" and i.code not in HIDDEN_WARNINGS]
        plain = is_plain(bp)
        L: list[str] = [PLAN_DRAFT_HEADING if errs else PLAN_HEADING, f"Goal: {clip(bp.get('mission'), GOAL_CLIP) or '(missing)'}", "What I understood you need:"]

        def need(label: str, value: object) -> None:
            L.append(f"- {label}: {clip(value) or '(not specified)'}")

        need("Scope", needs.get("scope"))
        if items(needs.get("inputs")):
            need("Your files (read-only)", ", ".join(items(needs.get("inputs"))))
        need("Quality bar", needs.get("quality_bar"))
        if s(needs.get("sources")) or not is_code(bp):
            need("Sources", needs.get("sources"))
        need("Workspace", needs.get("workspace") or "none (nothing writes files or runs commands)")
        if is_code(bp):
            code = mapping_or_empty(needs.get("code"))
            need("Tests / packaging / commits", "; ".join(f"{k}: {s(code.get(k)) or '?'}" for k in ("tests", "packaging", "commits")))
        L.append(f"- Models: {self._models_line(agents, needs)}")

        L.append(f"Team ({len(agents)} agents):")
        L += self._user_tree(agents) or ["- (none)"]
        L += self._user_budget(agents, bp)

        verifiers = [a for a in agents if a.kind == "verifier"]
        r = review_required(needs)
        if verifiers:
            L.append("Checking: " + ", ".join(v.name for v in verifiers) + " review"
                     + ("s" if len(verifiers) == 1 else "") + " the work independently (they did not write it); required changes go back "
                     f"to the author. I then re-check the final result against every {'success check' if plain else 'service check'} below.")
        else:
            L.append("Checking: no independent reviewer" + (" (you did not ask for one)" if r is False else " (!)")
                     + f". I still re-check the final result against every {'success check' if plain else 'service check'} below.")

        spec = ", ".join(x for x in (s(d.get("format")), f"max {d['max_words']} words" if d.get("max_words") else "") if x)
        if plain or d.get("description"):
            L.append(f"Deliverable: {clip(d.get('description')) or '(missing)'}" + (f" [{spec}]" if spec else ""))
            if s(d.get("path")):
                copied = any(i.code == "path-delivery" and i.path.startswith("needs.") for i in issues)
                L.append(f"  Delivered to: {s(d['path'])}" + (" (I copy it there after checking it)" if copied else " (the team writes it there)"))
            elif s(needs.get("workspace")) and is_code(bp):
                L.append(f"  Delivered to: the workspace {s(needs['workspace'])} (the team works and commits there)")
            else:
                L.append("  Delivered to: inside the organization folder (no location given)")

        if plain:
            crit = criteria_of(bp)
            L.append("Done when ALL of these hold:" if crit else "Done when: (no success checks given)")
            L += [f"  {i}. {' '.join(s(c).split())}" for i, c in enumerate(crit[:SHOWN_CRITERIA], 1)]  # the contract: in full
            if len(crit) > SHOWN_CRITERIA:
                L.append(f"  ... and {len(crit) - SHOWN_CRITERIA} more (see the details)")
        L += self._user_services(bp, agents)

        L.append(f"Checkpoints: approval - {clip(needs.get('approval')).rstrip('.') or 'this plan, before anything is built or started'}; "
                 f"progress - {clip(needs.get('progress')).rstrip('.') or 'one line when you ask'}; any spend beyond the budget needs your OK.")
        if warns:
            L.append(f"Warnings ({len(warns)}):")
            L += [f"- {clip(w.message)}" for w in warns[:SHOWN_WARNINGS]]
            if len(warns) > SHOWN_WARNINGS:
                L.append(f"- ... and {len(warns) - SHOWN_WARNINGS} more (see the details)")
        if errs:
            L.append(f"Errors ({len(errs)}):")
            L += [f"- {e.path}: {clip(e.message)}" for e in errs[:SHOWN_WARNINGS]]
        L.append("Nothing is created or started until you approve. Reply 'approve', or tell me what to change." if not errs
                 else "Cannot apply yet.")
        return "\n".join(L)

    def _user_tree(self, agents: Sequence[Agent]) -> list[str]:
        by = {a.addr: a for a in agents}
        out: list[str] = []

        def line(a: Agent, indent: int) -> None:
            out.append(f"{'  ' * indent}- {a.name} ({a.role}, model {a.model}): {self._access.describe(a)}")
            for c in a.children:
                line(by[c], indent + 1)

        for a in agents:
            if a.parent is None:
                line(a, 0)
        return out

    def _user_budget(self, agents: Sequence[Agent], bp: Mapping[str, object]) -> list[str]:
        needs, task = needs_of(bp), bp.get("task") if isinstance(bp.get("task"), dict) else {}
        est = self._budgets.estimate(agents) if agents else {"total": 0, "per": {}}
        cap = needs.get("budget_runs")
        if not is_plain(bp):  # services only: the budget is per request
            budgets = self._budgets.service_budgets(bp, agents)
            top = max(budgets.values(), default=0)
            out = [f"Budget: up to {top} runs per request (one run = one working session of one agent), "
                   + (f"your cap per request is {cap}" if cap else "you gave no cap") + f"; the minimum for one review and rework is {est['total']}. "
                   "Unspent runs come back to you."]
            if agents and len(budgets) == 1:
                split = self._budgets.budget_split(agents, top)
                for a in agents:
                    if a.children:
                        out.append(f"  {a.addr} starts with {split[a.addr]['grant']}, hands down "
                                   + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                                   + f" and keeps {split[a.addr]['keeps']} for planning, checking and rework.")
            if agents:
                out.append("If a check still fails after one rework, I'll come back to you with options before spending the reserve; "
                           "nothing beyond a request's budget is spent without your OK.")
            return out
        total = self._budgets.planned_total(bp, est["total"]) if agents else 0
        out = [f"Budget: {total} runs planned (one run = one working session of one agent), "
               + (f"your cap is {cap}" if cap else "you gave no cap") + f"; the minimum for one review and rework is {est['total']}. "
               "Unspent runs come back to you."]
        if agents:
            split = self._budgets.budget_split(agents, total)
            for a in agents:
                if a.children:
                    out.append(f"  {a.addr} starts with {split[a.addr]['grant']}, hands down "
                               + ", ".join(f"{c.rsplit('/', 1)[-1]} {split[c]['grant']}" for c in a.children)
                               + f" and keeps {split[a.addr]['keeps']} for planning, checking and rework.")
            out.append(self._failure_policy(total, est["total"]))
        return out

    def _failure_policy(self, total: int, minimum: int) -> str:
        """What happens when the check fails again after the one rework the budget is built for, with the reserve in runs.

        ``minimum`` = runs for one pass plus one rework cycle; what the plan holds above it is the reserve.
        """
        reserve = max(0, total - minimum)
        head = "If the check still fails after one rework, I'll come back to you with options"
        if reserve:
            return (f"{head} before spending the reserve (about {reserve} runs); nothing beyond the {total} planned "
                    "runs is spent without your OK.")
        return f"{head}; the plan has no reserve beyond that rework, and nothing beyond the {total} planned runs is spent without your OK."

    def _user_services(self, bp: Mapping[str, object], agents: Sequence[Agent]) -> list[str]:
        """The compact Services part of the plan for the user: per service what it is, what you provide, its budget,
        its checks (the contract, first few in full), where it is delivered; then the reflection rule and what runs now."""
        svcs = services_of(bp)
        if not svcs:
            return []
        budgets = self._budgets.service_budgets(bp, agents)
        top = next((a for a in agents if a.parent is None), None)
        out = ["Services (kept ready, requested whenever you want):"]
        for sv in svcs:
            name = s(sv.get("name"))
            crit = svc_criteria(sv)
            out.append(f"- {name}: {clip(sv.get('description'), 200) or '(missing)'}")
            out.append(f"  You provide: {self._words.input_words(sv)}")
            out.append(f"  Each request: up to {budgets[name]} runs")
            out.append("  Checks:" if crit else "  Checks: (none given)")
            out += [f"    {i}. {' '.join(c.split())}" for i, c in enumerate(crit[:SHOWN_SERVICE_CRITERIA], 1)]
            if len(crit) > SHOWN_SERVICE_CRITERIA:
                out.append(f"    ... and {len(crit) - SHOWN_SERVICE_CRITERIA} more (see the details)")
            out.append(f"  Delivered to: {self._words.delivery(sv, agents, bp)}")
        out.append(self._words.reflection_line(top.name if top else "the lead"))
        if is_request(bp):
            out.append(f"First request, started on approval: {s(task_of(bp).get('service'))}" + (f" ({self._words.request_words(bp)})" if self._words.request_words(bp) else "") + ".")
        elif not has_plain_task(bp):
            out.append("Nothing runs until you ask for a request: approving only creates the team and the services.")
        return out

    def _models_line(self, agents: Sequence[Agent], needs: Mapping[str, object]) -> str:
        """The plan's Models line: what the agents will really run on (the resolved ids), plus the stated policy if they differ."""
        used: dict[str, int] = {}
        for a in agents:
            used[a.model] = used.get(a.model, 0) + 1
        if not used:
            return f"{DEFAULT_MODEL} (no agents yet)"
        if len(used) == 1:
            return f"{next(iter(used))} for every agent"
        parts = ", ".join(f"{m} for {n} agent{'s' if n != 1 else ''}" for m, n in used.items())
        pol = clip(needs.get("model_policy")).rstrip(".")
        return f"{parts}" + (f" ({pol})" if pol else "")
