"""``ServiceBlueprintRules``: the ``services:`` list of a blueprint, and a first request in ``task``. Errors here block apply; they are written for the LLM."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from ..kernel import NAME_RE, JsonObject, OrgError
from ..services import DESCRIPTION_MAX, ContractNormalizer
from ._budgeting import TIGHT, round_offer
from ._protocols import BudgetPlanning, OrgContext, PathChecking, ServiceRules
from ._rules import delivers_directly, vague
from ._view import REQUEST_KEYS, SERVICE_KEYS, is_request, s, svc_criteria, svc_deliverable, unknown
from .api import Agent, Issue


class ServiceBlueprintRules(ServiceRules):
    def __init__(self, normalizer: ContractNormalizer, paths: PathChecking, budgets: BudgetPlanning) -> None:
        self._normalizer = normalizer
        self._paths = paths
        self._budgets = budgets

    def check(
        self, bp: Mapping[str, object], agents: Sequence[Agent], tops: Sequence[Agent], cap: int | None, est_total: int, org: OrgContext,
        roots: Sequence[Path], issues: list[Issue],
    ) -> None:
        raw = bp.get("services")
        if raw is None:
            if is_request(bp):
                issues.append(Issue("error", "task.service", "the task names a service but the blueprint has no `services:`; add the service, or give a plain task (to, title, goal, acceptance)", "service"))
            return
        if not isinstance(raw, list):
            issues.append(Issue("error", "services", "services must be a list: each item has name, description, inputs, acceptance, deliverable and budget", "service"))
            return
        top = tops[0] if len(tops) == 1 else None
        pcap = max(1, int(cast("int | str", org.config().get("playbook_max_words") or 1000)))
        taken: set[str] = set()
        other_names = org.service_names()
        by_name: dict[str, JsonObject] = {}
        for i, sv in enumerate(raw):
            if not isinstance(sv, dict):
                issues.append(Issue("error", f"services[{i}]", "a service is a mapping with name, description, inputs, acceptance, deliverable and budget", "service"))
                continue
            name = s(sv.get("name"))
            where = f"services[{name or i}]"
            unknown(sv, SERVICE_KEYS, where, issues)
            if not NAME_RE.fullmatch(name):
                issues.append(Issue("error", where, f"invalid service name '{name}': use lowercase letters, digits and dashes (max 32, starting with a letter), e.g. weekly-brief", "service-name"))
            elif name in taken:
                issues.append(Issue("error", where, f"duplicate service name '{name}'; requests name the service only, so each name must be unique", "service-name"))
            elif name in other_names:
                issues.append(Issue("error", where, f"a service called '{name}' already exists in this organization; requests name the service only, so pick another name", "service-name"))
            else:
                by_name[name] = sv
            taken.add(name)
            owner = s(sv.get("owner"))
            if owner and top is not None and owner != top.addr:
                issues.append(Issue("error", f"{where}.owner", f"owner '{owner}' must be the top-level agent ({top.addr}): root defines services only for its direct reports, so in this version a service is offered by the head of the team. Set owner: {top.addr} or leave it out", "service-owner"))
            desc = s(sv.get("description"))
            if not desc or len(desc) > DESCRIPTION_MAX or "\n" in desc:
                issues.append(Issue("error", f"{where}.description", f"description is one line of at most {DESCRIPTION_MAX} characters saying what the service delivers", "service"))
            try:
                self._normalizer.inputs(sv.get("inputs"))
            except OrgError as exc:
                issues.append(Issue("error", f"{where}.inputs", f"{exc}", "service-inputs"))
            crit = svc_criteria(sv)
            if not isinstance(sv.get("acceptance"), list) or not crit:
                issues.append(Issue("error", f"{where}.acceptance", "list the exact, checkable acceptance criteria (numbers, sections, formats, paths) as a YAML list: they are the contract of every request, and only the user can change them", "criteria"))
            else:
                vague(crit, f"{where}.acceptance", issues)
            d = svc_deliverable(sv)
            try:
                self._normalizer.deliverable(d)
            except OrgError as exc:
                issues.append(Issue("error", f"{where}.deliverable", f"{exc}", "deliverable"))
            else:
                if not s(d.get("format")):
                    issues.append(Issue("warning", f"{where}.deliverable.format", "no format given (e.g. markdown with a comparison table); the writer will guess", "deliverable-format"))
                mw = d.get("max_words")
                if mw and not any(str(mw) in c for c in crit):
                    issues.append(Issue("warning", f"{where}.acceptance", f"the {mw}-word limit is not in any criterion; add an exact criterion such as 'at most {mw} words (as counted by read)'", "limit-criterion"))
                if s(d.get("path")):
                    p = self._paths.check(d["path"], f"{where}.deliverable.path", issues, org, roots, what="deliverable path", dir_must_exist=False)
                    if p is not None:
                        if not delivers_directly(agents, p):
                            issues.append(Issue("warning", f"{where}.deliverable.path", f"no agent can write to {p} (agents write only inside their own directory or workspace); the assistant must copy each result there and verify it (the plan lists this step)", "path-delivery"))
                        if not p.parent.exists():
                            issues.append(Issue("warning", f"{where}.deliverable.path", f"{p.parent} does not exist; the copy step will create it", "path-parent"))
            b = sv.get("budget")
            if b is not None and (not isinstance(b, int) or isinstance(b, bool) or b < 1):
                issues.append(Issue("error", f"{where}.budget", "budget is the number of runs handed down with each request: a whole number >= 1", "service"))
            elif agents:
                round_runs = self._budgets.client_round(agents)
                total = self._budgets.service_budget(sv, est_total, cap, round_runs=round_runs)
                if cap is not None and total > cap:
                    issues.append(Issue("error", f"{where}.budget", f"planned budget {total} runs per request is above the user's cap of {cap} (the cap is for ONE request); lower the service's budget or shrink the team", "budget-cap"))
                if total < est_total:
                    issues.append(Issue("error", f"{where}.budget" if b is not None else "needs.budget_runs", f"{total} runs per request cannot cover the pipeline: the estimate with one review and one rework cycle is {est_total} (see estimate()); raise the budget or drop a role", "budget-low"))
                elif (offer := round_offer(total, est_total, round_runs)) is not None:
                    lead = top.name if top is not None else "the top agent"
                    issues.append(Issue("warning", f"{where}.budget" if b is not None else "needs.budget_runs", f"{total} runs per request covers one pass and one internal rework (the estimate is {est_total}), not a round of your questions or a rejection, which takes about {round_runs} more (1, plus 2 for each agent below {lead}): {offer} per request covers one such round", "budget-tight"))
                elif total < math.ceil(est_total * TIGHT):
                    issues.append(Issue("warning", f"{where}.budget", f"{total} runs per request leaves almost no slack over the estimate of {est_total}; expect a stall on the first surprise", "budget-tight"))
            if sv.get("playbook") is not None:
                pb = sv["playbook"]
                words = len(pb.split()) if isinstance(pb, str) else 0
                if not isinstance(pb, str) or not pb.strip():
                    issues.append(Issue("error", f"{where}.playbook", "playbook is the workflow as markdown text (steps: who does what, in which order, which check); leave it out to get a generated one", "playbook"))
                elif words > pcap:
                    issues.append(Issue("error", f"{where}.playbook", f"the playbook is {words} words; the limit is {pcap} (playbook_max_words): condense it to the steps that matter", "playbook"))
            if "locked" in sv and not isinstance(sv["locked"], bool):
                issues.append(Issue("error", f"{where}.locked", "locked is true or false (true: the team lead may not improve the playbook)", "service"))
        if not any(isinstance(x, dict) for x in raw):
            issues.append(Issue("error", "services", "services is empty: add at least one service, or remove the key", "service"))
        if is_request(bp):
            self._request(cast(JsonObject, bp["task"]), by_name, top, issues)

    def _request(self, task: JsonObject, by_name: Mapping[str, JsonObject], top: Agent | None, issues: list[Issue]) -> None:
        """``task: {service, inputs, title, note}``: a first request, checked like ``request()`` checks it."""
        name = s(task.get("service"))
        sv = by_name.get(name)
        if sv is None:
            issues.append(Issue("error", "task.service", f"'{name}' is not one of the blueprint's services ({', '.join(by_name) or 'none'}); name one of them", "service"))
            return
        if s(task.get("to")) and top is not None and s(task.get("to")) != top.addr:
            issues.append(Issue("error", "task.to", f"'{s(task.get('to'))}' must be the top-level agent ({top.addr}), the owner of the service; leave `to` out", "task"))
        raw_given = task.get("inputs")
        if raw_given is not None and not isinstance(raw_given, dict):
            issues.append(Issue("error", "task.inputs", "for a request, inputs is a mapping {input name: value}", "service-request"))
            return
        given = {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in (cast(JsonObject, raw_given) or {}).items()}
        try:
            known = {str(i["name"]): i for i in self._normalizer.inputs(sv.get("inputs"))}
        except OrgError:
            return  # reported on the service itself
        missing_names = [k for k in given if k not in known]
        if missing_names:
            issues.append(Issue("error", "task.inputs", f"unknown input(s) for `{name}`: {', '.join(missing_names)}. Its inputs: {', '.join(known) or 'none'}", "service-request"))
        missing = [n for n, i in known.items() if i["required"] and not given.get(n)]
        if missing:
            issues.append(Issue("error", "task.inputs", f"missing required input(s) for `{name}`: {', '.join(missing)}; give them under task.inputs", "service-request"))
