"""``TextPlanDetails``: the full plan, for the assistant (the user is shown the block of ``_userplan``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._protocols import AccessReport, BudgetPlanning, PlanBasis, PlanDetailing, PlanWords, PlaybookWriting
from ._provenance import source_line
from ._rules import is_code, review_required
from ._view import (
    criteria_entries,
    criteria_of,
    deliverable_of,
    is_plain,
    is_request,
    mapping_or_empty,
    needs_of,
    s,
    services_of,
    svc_criteria,
    svc_criteria_entries,
    svc_deliverable,
    task_of,
)
from .api import Agent, Issue


class TextPlanDetails(PlanDetailing):
    def __init__(
        self, basis: PlanBasis, budgets: BudgetPlanning, access: AccessReport, playbooks: PlaybookWriting, words: PlanWords,
    ) -> None:
        self._basis = basis
        self._budgets = budgets
        self._access = access
        self._playbooks = playbooks
        self._words = words

    def render(self, bp: Mapping[str, object], issues: Sequence[Issue] | None, allowed_roots: Sequence[str | Path] | None) -> str:
        """The plan the user approves: goal, needs, org tree, budget, review, deliverable, checkpoints, warnings."""
        if issues is None:
            issues = self._basis.issues(bp, allowed_roots)
        agents = self._basis.agents(bp, allowed_roots)
        needs, d = needs_of(bp), deliverable_of(bp)
        task = task_of(bp)
        errs = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level == "warning"]
        mission = s(bp.get("mission")) or "(missing)"
        L: list[str] = ["# Plan for approval", "", f"Goal: {mission}", "", "Needs as understood:"]

        def need(label: str, value: object) -> None:
            L.append(f"- {label}: {s(value) or '(not specified)'}")

        need("Scope", needs.get("scope"))
        spec = ", ".join(x for x in (s(d.get("format")), f"max {d['max_words']} words" if d.get("max_words") else "") if x)
        need("Deliverable", (s(d.get("description")) + (f" [{spec}]" if spec else "")) if d.get("description")
             else ("per service (see Services below)" if not is_plain(bp) else ""))
        need("Quality bar", needs.get("quality_bar"))
        need("Sources / tools", needs.get("sources"))
        need("Workspace", needs.get("workspace") or "none (no agent writes files or runs commands)")
        if is_code(bp):
            code = mapping_or_empty(needs.get("code"))
            need("Tests / packaging / commits", "; ".join(f"{k}: {s(code.get(k)) or '?'}" for k in ("tests", "packaging", "commits")))
        need("Model policy", needs.get("model_policy"))
        r = review_required(needs)
        need("Review", "required" if r else ("not required" if r is False else None))

        L += ["", f"Organization ({len(agents)} agents):"]
        L += self._tree_lines(agents) or ["- (none)"]

        est = self._budgets.estimate(agents) if agents else {"total": 0, "per": {}}
        plain = is_plain(bp)
        total = self._budgets.planned_total(bp, est["total"]) if agents else 0
        budget = task.get("budget")
        if isinstance(budget, int) and plain:
            total = budget
        cap = needs.get("budget_runs")
        svc_budgets = self._budgets.service_budgets(bp, agents)

        def split_lines(total: int, indent: str = "  ") -> None:
            split = self._budgets.budget_split(agents, total)
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
            round_runs = self._budgets.client_round(agents)
            L += ["", "Budget per request" + (f" (your cap: {cap})" if cap else " (no cap given)") + f", estimate {est['total']} for one pass + one review/rework cycle"
                  + (f", {est['total'] + round_runs} with one round of your questions or a rejection" if round_runs else "") + ":",
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
        L.append(f"- {s(d.get('description')) or ('per service (see Services below)' if not plain else '(missing)')}" + (f" ({spec})" if spec else ""))
        if s(d.get("path")):
            copy = any(i.code == "path-delivery" and i.path.startswith("needs.") for i in issues)
            L.append(f"- Final location: {s(d['path'])}" + (" (copied there by the assistant after verification)" if copy else " (written there by the team)"))
        elif plain or d.get("description"):
            L.append("- Final location: inside the organization (no path given)")

        if plain:
            L += ["", f"First task: to {s(task.get('to')) or (agents[0].addr if agents else '?')}: {s(task.get('title')) or '(missing)'}"]
            crit = criteria_of(bp)
            for i, (c, entry) in enumerate(zip(crit, criteria_entries(bp)), 1):
                L += [f"  {i}. {c}", f"     {source_line(entry)}"]
            if not crit:
                L.append("  (no acceptance criteria)")
        if services_of(bp):
            L += ["", f"Services ({len(services_of(bp))}), offered by {agents[0].addr if agents else '?'} and defined by root (the contract: only root can change it):"]
            for sv in services_of(bp):
                name = s(sv.get("name"))
                sd = svc_deliverable(sv)
                ssp = ", ".join(x for x in (s(sd.get("format")), f"max {sd['max_words']} words" if sd.get("max_words") else "") if x)
                L += [f"- {name}: {s(sv.get('description')) or '(missing)'}", f"  inputs: {self._words.input_words(sv)}",
                      f"  budget: {svc_budgets.get(name, 0)} runs per request" + (", locked (the lead may not revise the playbook)" if sv.get("locked") is True else ""),
                      f"  deliverable: {s(sd.get('description')) or '(missing)'}" + (f" [{ssp}]" if ssp else "") + f"; delivered to: {self._words.delivery(sv, agents, bp)}",
                      "  acceptance (the contract, travels with every request):"]
                for i, (c, entry) in enumerate(zip(svc_criteria(sv), svc_criteria_entries(sv)), 1):
                    L += [f"    {i}. {c}", f"       {source_line(entry)}"]
                if not svc_criteria(sv):
                    L.append("    (none)")
                pb = sv.get("playbook")
                L.append("  playbook v1: " + (f"given in the blueprint ({len(pb.split())} words)" if isinstance(pb, str) and pb.strip() else "generated from the team (steps, budget plan):"))
                if not (isinstance(pb, str) and pb.strip()) and agents:
                    L += ["    " + ln for ln in self._playbooks.default_playbook(agents[0], agents, sv, svc_budgets.get(name, 0)).splitlines()]
            L.append(self._words.reflection_line(agents[0].name if agents else "lead"))
            if is_request(bp):
                L.append(f"First request: service {s(task.get('service'))}" + (f": {self._words.request_words(bp)}" if self._words.request_words(bp) else "") + (f"; title: {s(task.get('title'))}" if s(task.get("title")) else ""))
            elif not plain:
                L.append("No first task: nothing runs until you ask for a request (request(service, inputs), then start()).")

        L += ["", "Checkpoints:",
              f"- Approval: {s(needs.get('approval')) or 'plan approval before anything is built or started (default)'}",
              f"- Progress: {s(needs.get('progress')) or 'one line on request (default)'}",
              "- Any spend beyond the budget needs your OK."]

        if warns:
            L += ["", f"Warnings ({len(warns)}):"] + [f"- {w.path}: {w.message}" for w in warns]
        if errs:
            L += ["", f"Errors ({len(errs)}) - must be fixed before this can be applied:"] + [f"- {e.path}: {e.message}" for e in errs]
        L.append("")
        L.append("Cannot apply yet: tell me what to change." if errs else "Reply 'approve' or tell me what to change.")
        return "\n".join(L)

    def _tree_lines(self, agents: Sequence[Agent]) -> list[str]:
        by = {a.addr: a for a in agents}
        out: list[str] = []

        def line(a: Agent, indent: int) -> None:
            tpl = f"[{a.template.name}]" if a.template else "[custom]"
            ws = f" ws={a.workspace}" if a.workspace else ""
            out.append(f"{'  ' * indent}- {a.name} {tpl} {a.role}: model={a.model}, tools={','.join(a.tools) or 'none'}{ws}")
            access = self._access.line(a)
            if access:
                out.append(f"{'  ' * indent}  Access: {access}")
            for c in a.children:
                line(by[c], indent + 1)

        for a in agents:
            if a.parent is None:
                line(a, 0)
        return out
