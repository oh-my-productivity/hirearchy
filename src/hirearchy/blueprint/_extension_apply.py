"""``ExtensionApplier``: an approved extension becomes changes to the organization (design 5.5)."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..agents import AgentRegistry
from ..hierarchy import Hiring, Retirement
from ..kernel import ROOT, RUNTIME, EventSink, clip, join_frontmatter
from ..dispatch import MessageSender
from ..services import ContractNormalizer, ServiceCommands
from ..settings import OrgLimits
from ..snapshots import OrgSnapshotter
from ._added import checker_line, limits_line, with_changes
from ._extension_org import Reads
from ._protocols import Charters, ExtensionResolution, ExtensionUndoing, PlaybookWriting
from ._shapes import Extension, Undo
from ._view import criterion_source, needs_of, s, svc_criteria, svc_criteria_entries, svc_deliverable
from .api import BlueprintError, ExtensionApplying, PlanIdentity, errors

EXTEND_STALE = (
    "not applied: plan_id does not match this change against the organization as it is now (the blueprint, or something it names: an agent, a service, "
    "a limit or a schedule, changed since propose_org), so this is not the plan the user approved. Call propose_org(blueprint, extend=\"current\") again, "
    "show the new PLAN FOR YOU block, and apply only after their approval."
)
HAS_ERRORS = "blueprint has errors, nothing was created:\n"
NOT_APPLIED = "not applied: {error}. Everything this change wrote was taken back.{budget}"
PARTLY = "partly applied: {done} retired; {name} failed ({error}); everything before the retires was applied. Tell the user."
NOTE_TITLE = "A checker joined your team"
NOTE = "{agent} ({role}) joined your team to check {services}."
NOTE_STEP = (
    'Add its step to the playbook of {service}: revise_playbook(op="add", kind="step", text="Before you report a request of {service}, send the draft to '
    '{address} and apply its FAIL items for {criteria}.", evidence=[{evidence}])'
)
NOT_TOLD = "({owner} was not told: {error})"
NOTHING_RUNS = "Nothing runs because of it."
SERVICES_READY = "Nothing runs yet: the services are ready. When the user asks for one, call request(service, inputs) (see services()), then start() if the scheduler is not running."
_IDS = re.compile(r"\b([CR]\d+)\b")


def _ids(prefix: str, *texts: str) -> list[str]:
    return list(dict.fromkeys(i for text in texts for i in _IDS.findall(text) if i.startswith(prefix)))


class ExtensionApplier(ExtensionApplying):
    def __init__(
        self, reads: Reads, resolver: ExtensionResolution, identity: PlanIdentity, charters: Charters, playbooks: PlaybookWriting,
        normalizer: ContractNormalizer, hiring: Hiring, retirement: Retirement, registry: AgentRegistry, commands: ServiceCommands, limits: OrgLimits,
        sender: MessageSender, undo: ExtensionUndoing, snapshots: OrgSnapshotter, events: EventSink,
    ) -> None:
        self._reads = reads
        self._resolver = resolver
        self._identity = identity
        self._charters = charters
        self._playbooks = playbooks
        self._normalizer = normalizer
        self._hiring = hiring
        self._retirement = retirement
        self._registry = registry
        self._commands = commands
        self._limits = limits
        self._sender = sender
        self._undo = undo
        self._snapshots = snapshots
        self._events = events

    def apply(
        self, bp: Mapping[str, object], *, plan_id: str | None, require_sources: bool = False, allowed_roots: Sequence[str | Path] | None = None,
    ) -> str:
        ext = self._resolver.resolve(bp, allowed_roots=allowed_roots, require_sources=require_sources)  # 1: against the files as they are now
        problems = errors(ext.issues)
        if problems:
            raise BlueprintError(HAS_ERRORS + "\n".join(f"- {i.path}: {i.message}" for i in problems))
        pid = self._identity.plan_id(bp)  # 2: the extension and the organization as it is now
        if plan_id is not None and plan_id.strip() != pid:
            raise BlueprintError(EXTEND_STALE)
        journal: list[Undo] = []
        step = "limits"
        try:
            step = self._limits_step(ext, pid, journal)
            step = self._additions(bp, ext, pid, journal)
            step = self._changes(ext, pid, journal)
        except Exception as error:
            budget = self._undo.undo(journal, pid)
            self._events.emit("extension.rolled_back", actor=ROOT, plan_id=pid, step=step, error=clip(str(error), 500))
            raise BlueprintError(NOT_APPLIED.format(error=str(error).rstrip("."), budget=budget)) from error
        done, failure = self._retires(ext, pid)
        if failure is not None and not done:  # nothing irreversible happened yet: take everything back
            budget = self._undo.undo(journal, pid)
            self._events.emit("extension.rolled_back", actor=ROOT, plan_id=pid, step=failure[0], error=clip(str(failure[1]), 500))
            raise BlueprintError(NOT_APPLIED.format(error=str(failure[1]).rstrip("."), budget=budget)) from failure[1]
        told = self._notes(ext)
        self._commit(ext, pid)
        if failure is not None:
            self._events.emit("extension.partial", actor=ROOT, plan_id=pid, done=done, failed=failure[0], error=clip(str(failure[1]), 500))
            raise BlueprintError(PARTLY.format(done=", ".join(done), name=failure[0], error=str(failure[1]).rstrip("."))) from failure[1]
        return self._reply(ext, pid, done, told)

    # ------------------------------------------------------------------ 3: limits, first (the hiring rules check them for every addition)

    def _limits_step(self, ext: Extension, pid: str, journal: list[Undo]) -> str:
        step = "limits"
        for c in ext.limits:
            step = f"limits of {c.agent}"
            meta, body = self._reads.charters.charter(c.agent)
            old = join_frontmatter(meta, body)
            new = dict(meta)
            if c.can_hire is not None:
                new["can_hire"] = c.can_hire
            if c.max_children is not None:
                new["max_children"] = c.max_children
            text = limits_line(int(str(new.get("max_children", 0))), bool(new.get("can_hire")))
            self._registry.rewrite_charter(c.agent, join_frontmatter(new, with_changes(body, [], [], text, pid)))
            journal.append(Undo("charter", c.agent, text=old))
        if ext.depth is not None:
            step = "max_depth"
            journal.append(Undo("depth", number=self._limits.set_max_depth(ext.depth.value)))
        return step

    # ------------------------------------------------------------------ 4: the agents and services it adds

    def _additions(self, bp: Mapping[str, object], ext: Extension, pid: str, journal: list[Undo]) -> str:
        step = "agents"
        approval = f"change {pid}"
        for a in ext.agents:  # parents first
            step = f"hire {a.addr}"
            below = [x for x in ext.agents if x.addr.startswith(a.addr + "/")]
            charter = self._charters.extension_charter(a, below, pid, ext.extras.get(a.addr, ""))
            addr = self._hiring.hire(
                a.parent or ROOT, a.name, a.role, charter, model=a.model, tools=a.tools, can_hire=a.can_hire, max_children=a.max_children,
                workspace=a.workspace, inputs=a.inputs if (a.inputs or "read" in a.tools) else None, approved=True, kind=a.kind, approved_in=approval,
            )
            journal.append(Undo("agent", addr))
        words = s(needs_of(bp).get("elicitation"))
        for sv in ext.services:
            step = f"define {sv.name}"
            e = sv.entry
            deliverable = dict(self._normalizer.deliverable(svc_deliverable(e)))
            if deliverable.get("path"):
                deliverable["path"] = os.path.expanduser(str(deliverable["path"]))
            sources = [criterion_source(entry) for entry in svc_criteria_entries(e)]
            team = ext.teams[sv.owner]
            owner = next(x for x in team if x.addr == sv.owner)
            given = e.get("playbook")
            playbook = None if sv.continues is not None else given.strip() if isinstance(given, str) and given.strip() else self._playbooks.default_playbook(
                owner, team, e, sv.budget,
            )
            self._commands.define_service(
                ROOT, sv.owner, sv.name, description=s(e.get("description")), inputs=self._normalizer.inputs(e.get("inputs")), acceptance=svc_criteria(e),
                deliverable=deliverable, budget=sv.budget, playbook=playbook, locked=e.get("locked") is True, sources=sources if any(sources) else None,
                elicitation=words or None, approved_in=approval,
            )
            journal.append(Undo("service", sv.owner, sv.name))
        return step

    # ------------------------------------------------------------------ 5: the changes: charter lines and budgets

    def _changes(self, ext: Extension, pid: str, journal: list[Undo]) -> str:
        step = "charter lines"
        by_agent: dict[str, tuple[list[str], list[str]]] = {}
        for c in ext.lines:
            by_agent.setdefault(c.agent, ([], []))[0].append(c.line)
        for ch in ext.checkers:
            agent = next(a for a in ext.agents if a.addr == ch.agent)
            by_agent.setdefault(ch.owner, ([], []))[0].append(checker_line(ch.agent, agent.role, ch.services, ext.extras.get(ch.agent, "")))
        for c in ext.removals:
            by_agent.setdefault(c.agent, ([], []))[1].append(c.line)
        for addr, (add, remove) in by_agent.items():
            step = f"charter lines of {addr}"
            meta, body = self._reads.charters.charter(addr)
            old = join_frontmatter(meta, body)
            self._registry.rewrite_charter(addr, join_frontmatter(meta, with_changes(body, add, remove, None, pid)))
            journal.append(Undo("charter", addr, text=old))
        for b in ext.budgets:
            step = f"budget of {b.service}"
            contract = self._reads.services.read_contract(b.owner, b.service)
            self._commands.define_service(ROOT, b.owner, b.service, budget=b.budget)
            journal.append(Undo("budget", b.owner, b.service, number=b.was, version=contract.version if contract is not None else 0))
        return step

    # ------------------------------------------------------------------ 7 and 8: the retires, last because they cannot be undone

    def _retires(self, ext: Extension, pid: str) -> tuple[list[str], tuple[str, Exception] | None]:
        done: list[str] = []
        approval = f"change {pid}"
        for r in ext.service_retires:
            name = f"service {r.service} of {r.owner}"
            try:
                self._commands.retire_service(ROOT, r.owner, r.service, r.reason, approved_in=approval)
            except Exception as error:
                return done, (name, error)
            done.append(name)
        for g in ext.retires:
            try:
                self._retirement.retire_team(ROOT, g.agent, g.reason, approved_in=approval)
            except Exception as error:
                return done, (g.agent, error)
            done.append(g.agent)
        return done, None

    # ------------------------------------------------------------------ 9: the owner is told, only now, so a note is never sent for a change taken back

    def _notes(self, ext: Extension) -> list[str]:
        told: list[str] = []
        for ch in ext.checkers:
            agent = next(a for a in ext.agents if a.addr == ch.agent)
            extra = ext.extras.get(ch.agent, "")
            criteria = ", ".join(_ids("C", ext.reason, extra)) or "its criteria"
            evidence = ", ".join(f'"{i}"' for i in _ids("R", ext.reason, extra)) or "<the R ids of the rejections you were shown>"
            body = "\n".join([
                NOTE.format(agent=ch.agent, role=agent.role, services=", ".join(ch.services)),
                *(NOTE_STEP.format(service=name, address=ch.agent, criteria=criteria, evidence=evidence) for name in ch.services),
            ])
            try:
                self._sender.send(RUNTIME, ch.owner, body, type="note", title=NOTE_TITLE, wake=True)
            except Exception as error:
                self._events.emit("team_note.failed", actor=ROOT, owner=ch.owner, agent=ch.agent, error=clip(str(error), 500))
                told.append(NOT_TOLD.format(owner=ch.owner, error=str(error).rstrip(".")))
        return told

    # ------------------------------------------------------------------ 10: the commit, and the reply

    def _commit(self, ext: Extension, pid: str) -> None:
        lines = len(ext.lines) + len(ext.removals) + len(ext.checkers)
        gone = sum(len(r.team) for r in ext.retires)
        subject = (
            f"root: applied extension {pid} ({clip(ext.reason, 80)}): +{len(ext.agents)} agents, +{len(ext.services)} services, {lines} lines, "
            f"{len(ext.limits) + (1 if ext.depth is not None else 0)} limits, -{gone} agents"
        )
        try:
            self._snapshots.commit(subject)
        except Exception:  # noqa: BLE001 - a snapshot is a convenience: the change is applied
            pass

    def _reply(self, ext: Extension, pid: str, retired: Sequence[str], told: Sequence[str]) -> str:
        out: list[str] = []
        if ext.agents:
            out.append(f"added {len(ext.agents)} agent(s): {', '.join(a.addr for a in ext.agents)}")
        if ext.services:
            out.append(f"defined {len(ext.services)} service(s): {', '.join(f'{sv.name} of {sv.owner}' for sv in ext.services)} (contract and playbook)")
        if ext.limits or ext.depth is not None:
            out.append("changed limits: " + ", ".join([*(c.agent for c in ext.limits), *(["max_depth"] if ext.depth is not None else [])]))
        if ext.lines or ext.removals or ext.checkers:
            out.append(f"charter lines: {len(ext.lines) + len(ext.checkers)} added, {len(ext.removals)} taken out")
        out += [f"budget of {b.service} of {b.owner}: {b.was} -> {b.budget} runs per request" for b in ext.budgets]
        if retired:
            out.append("retired: " + ", ".join(retired))
        out += [f"warning: {i.path}: {i.message}" for i in ext.issues if i.level == "warning"]
        out += told
        nxt = SERVICES_READY if ext.services else NOTHING_RUNS
        return f"applied the change {pid} to {self._reads.org.root()}\n" + "\n".join(out) + f"\n{nxt}"
