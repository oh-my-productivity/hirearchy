"""``TextExtensionPlan``: the plan of an extension for the user and for the assistant (design 5.3)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..kernel import ROOT
from ._added import checker_line
from ._extension_org import Reads
from ._plan_texts import PLAN_DRAFT_HEADING, SHOWN_SERVICE_CRITERIA, SHOWN_WARNINGS, shown_warnings
from ._protocols import AccessWording, Charters, ExtensionPlanning, ExtensionResolution, Fingerprinting, PlanWords
from ._provenance import source_line
from ._shapes import AddedService, Extension, ExtensionText
from ._text import clip
from ._view import s, svc_criteria, svc_criteria_entries
from .api import Agent, PlanIdentity

HEADING = "PLAN FOR YOU (a change to your organization)"
NOW = "Your organization now: {a} agents, {s} service(s){names}."
LIMITS = "- {agent}: may have up to {m} direct reports (was {m0}){hire}{free}"
HIRE = "; may hire: {now} (was {was})"
FREE = ", so it may add {f} worker(s) without asking you"
LINE_ADDED = '- the charter of {agent} gets the line: "{line}"'
LINE_REMOVED = '- the charter of {agent} loses the line it got from an earlier change: "{line}"'
BUDGET_CHANGED = "- {service} of {owner}: up to {b} runs per request (was {b0})"
DEPTH = "- the organization's depth: up to {d} levels (was {d0})"
TOLD = "- {owner} is told that {address} joined its team (one run of {owner} when it next runs)"
SERVICE_REMOVED = "- service {name} of {owner}: no new requests; its contract, playbook and cases are kept (defining it again continues them)"
AGENT_REMOVED = "- {agent} and its team ({k} agents): its open tasks are closed as failed; its unspent runs come back.{kept}"
KEPT_SERVICES = " Its services ({names}) go with it into the archive."
BUDGET_LINE = "Budget: {lines}; nothing else changes what a request costs."
UNCHANGED = "Unchanged: {a} agents and {s} service(s), their charters, contracts and playbooks."
APPROVE = "Nothing changes until you approve. Reply 'approve', or tell me what to change."
CONTINUES = " (defines {name} again: its contract, playbook and cases continue)"


class TextExtensionPlan(ExtensionPlanning):
    def __init__(
        self, resolver: ExtensionResolution, reads: Reads, access: AccessWording, words: PlanWords, charters: Charters, identity: PlanIdentity,
        fingerprint: Fingerprinting,
    ) -> None:
        self._resolver = resolver
        self._reads = reads
        self._access = access
        self._words = words
        self._charters = charters
        self._identity = identity
        self._fingerprint = fingerprint

    def plan(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False) -> ExtensionText:
        ext = self._resolver.resolve(bp, allowed_roots=allowed_roots, require_sources=require_sources)
        failed = any(i.level == "error" for i in ext.issues)
        return ExtensionText(self._block(ext, failed), self._details(bp, ext, failed), ext.issues)

    # ------------------------------------------------------------------ the block for the user

    def _block(self, ext: Extension, failed: bool) -> str:
        lines = [PLAN_DRAFT_HEADING if failed else HEADING, f"Why: {clip(ext.reason)}"]
        if not failed or ext.teams or ext.agents or ext.services:
            lines.append(self._now())
        for group, entries in (("Adds:", self._adds(ext)), ("Changes:", self._changes(ext)), ("Removes:", self._removes(ext))):
            if entries:
                lines += [group, *entries]
        budgets = [f"{b.service} of {b.owner}: up to {b.budget} runs per request (was {b.was})" for b in ext.budgets]
        budgets += [f"{sv.name} of {sv.owner}: up to {sv.budget} runs per request" for sv in ext.services]
        if budgets:
            lines.append(BUDGET_LINE.format(lines="; ".join(budgets)))
        if not failed:
            lines.append(self._unchanged(ext))
        warns = shown_warnings(ext.issues)
        errs = [i for i in ext.issues if i.level == "error"]
        if warns:
            lines.append(f"Warnings ({len(warns)}):")
            lines += [f"- {clip(w.message)}" for w in warns[:SHOWN_WARNINGS]]
            if len(warns) > SHOWN_WARNINGS:
                lines.append(f"- ... and {len(warns) - SHOWN_WARNINGS} more (see the details)")
        if errs:
            lines.append(f"Errors ({len(errs)}):")
            lines += [f"- {e.path}: {clip(e.message)}" for e in errs[:SHOWN_WARNINGS]]
        lines.append("Cannot apply yet." if failed else APPROVE)
        return "\n".join(lines)

    def _now(self) -> str:
        reads = self._reads
        names = sorted(reads.org.service_names())
        return NOW.format(a=len(reads.agents.agents()), s=len(names), names=f": {', '.join(names)}" if names else "")

    def _adds(self, ext: Extension) -> list[str]:
        out: list[str] = []
        for a in ext.agents:
            parent = "you" if a.parent in (None, ROOT) else a.parent
            out.append(f"- {a.addr} ({a.role}, model {a.model}, reports to {parent}): {self._access.describe(a)}")
        for sv in ext.services:
            out += self._service(sv, ext)
        return out

    def _service(self, sv: AddedService, ext: Extension) -> list[str]:
        e = sv.entry
        team = ext.teams.get(sv.owner, [])
        out = [f"- service {sv.name} of {sv.owner}" + (CONTINUES.format(name=sv.name) if sv.continues is not None else "") + f": {clip(e.get('description'), 200)}"]
        out.append(f"  You provide: {self._words.input_words(e)}. Each request: up to {sv.budget} runs, sent only when you ask.")
        criteria = svc_criteria(e)
        out.append("  Checks:" if criteria else "  Checks: (none given)")
        for i, (text, entry) in enumerate(zip(criteria[:SHOWN_SERVICE_CRITERIA], svc_criteria_entries(e)), 1):
            out += [f"    {i}. {' '.join(text.split())}", f"       {source_line(entry, self._dates(entry))}"]
        if len(criteria) > SHOWN_SERVICE_CRITERIA:
            out.append(f"    ... and {len(criteria) - SHOWN_SERVICE_CRITERIA} more (see the details)")
        out.append(f"  Delivered to: {self._words.delivery(e, team, {})}")
        return out

    def _dates(self, entry: object) -> str:
        """When root sent the one-off tasks a criterion was copied from (a date each, oldest first)."""
        ids = entry.get("from_tasks") if isinstance(entry, dict) else None
        found = [self._reads.tasks.task(s(x)) for x in ids] if isinstance(ids, list) else []
        return ", ".join(sorted({f"{t.created:%Y-%m-%d}" for t in found if t is not None and t.created is not None}))

    def _changes(self, ext: Extension) -> list[str]:
        reads, out = self._reads, []
        for c in ext.limits:
            m = c.max_children if c.max_children is not None else c.was_max_children
            now = c.can_hire if c.can_hire is not None else c.was_can_hire
            added = sum(1 for a in ext.agents if a.parent == c.agent)
            free = m - len(reads.agents.children(c.agent)) - added if now else 0
            out.append(LIMITS.format(
                agent=c.agent, m=m, m0=c.was_max_children, hire=HIRE.format(now="yes" if now else "no", was="yes" if c.was_can_hire else "no") if now != c.was_can_hire else "",
                free=FREE.format(f=free) if free > 0 else "",
            ))
        out += [LINE_ADDED.format(agent=c.agent, line=c.line) for c in ext.lines]
        for ch in ext.checkers:
            agent = next(a for a in ext.agents if a.addr == ch.agent)
            out.append(LINE_ADDED.format(agent=ch.owner, line=checker_line(ch.agent, agent.role, ch.services, ext.extras.get(ch.agent, ""))))
            out.append(TOLD.format(owner=ch.owner, address=ch.agent))
        out += [LINE_REMOVED.format(agent=c.agent, line=c.line) for c in ext.removals]
        out += [BUDGET_CHANGED.format(service=b.service, owner=b.owner, b=b.budget, b0=b.was) for b in ext.budgets]
        if ext.depth is not None:
            out.append(DEPTH.format(d=ext.depth.value, d0=ext.depth.was))
        return out

    def _removes(self, ext: Extension) -> list[str]:
        reads, out = self._reads, []
        out += [SERVICE_REMOVED.format(name=r.service, owner=r.owner) for r in ext.service_retires]
        for r in ext.retires:
            owned = sorted({n for a in r.team if "/" not in a for n in reads.services.service_names(a)})
            out.append(AGENT_REMOVED.format(agent=r.agent, k=len(r.team), kept=KEPT_SERVICES.format(names=", ".join(owned)) if owned else ""))
        return out

    def _unchanged(self, ext: Extension) -> str:
        reads = self._reads
        gone = {a for r in ext.retires for a in r.team}
        touched = {c.agent for c in ext.limits} | {c.agent for c in ext.lines} | {c.agent for c in ext.removals} | {c.owner for c in ext.checkers}
        stay = [a for a in reads.agents.agents() if a not in gone and a not in touched]
        retired = {(r.owner, r.service) for r in ext.service_retires} | {(b.owner, b.service) for b in ext.budgets}
        services = [(a, n) for a in reads.agents.children(ROOT) if a not in gone for n in reads.services.service_names(a) if (a, n) not in retired]
        return UNCHANGED.format(a=len(stay), s=len(services))

    # ------------------------------------------------------------------ the details for the assistant

    def _details(self, bp: Mapping[str, object], ext: Extension, failed: bool) -> str:
        pid = "(none: the extension has errors)" if failed else self._identity.plan_id(bp)
        out = [f"Extension: {ext.reason}", f"Plan id: {pid}"]
        for a in ext.agents:
            out.append(f"Added agent {a.addr}: role {a.role}; kind {a.kind}; model {a.model}; tools {', '.join(a.tools) or 'none'}; workspace {a.workspace or 'none'}; "
                       f"inputs {', '.join(a.inputs) or 'none'}; can_hire {a.can_hire}; max_children {a.max_children}")
            out.append(f"Charter of {a.addr}:\n{self._charters.extension_charter(a, self._team_below(a, ext.agents), pid, ext.extras.get(a.addr, ''))}")
        for sv in ext.services:
            out.append(f"Added service {sv.name} of {sv.owner}: {sv.budget} runs per request; criteria {len(svc_criteria(sv.entry))}"
                       + (f"; continues the retired copy ({len(sv.continues)} criteria)" if sv.continues is not None else ""))
        for c in ext.limits:
            changed = [f"max_children {c.was_max_children} -> {c.max_children}"] if c.max_children is not None else []
            changed += [f"can_hire {c.was_can_hire} -> {c.can_hire}"] if c.can_hire is not None else []
            out.append(f"Limit {c.agent}: {'; '.join(changed)}")
        if ext.depth is not None:
            out.append(f"Depth: max_depth {ext.depth.was} -> {ext.depth.value}")
        out += [f"Retire {r.agent} (team {', '.join(r.team)}): {r.reason}" for r in ext.retires]
        out += [f"Retire service {r.service} of {r.owner}: {r.reason}" for r in ext.service_retires]
        if not failed:
            out.append(f"Fingerprint of the organization it touches: {self._fingerprint.fingerprint(bp)}")
        out += [i.render() for i in ext.issues]
        return "\n".join(out)

    @staticmethod
    def _team_below(a: Agent, agents: Sequence[Agent]) -> list[Agent]:
        return [x for x in agents if x.addr.startswith(a.addr + "/")]
