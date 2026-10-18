# mypy: ignore-errors
"""Membership of the agent tree: hire and retire (hierarchy).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from typing import NamedTuple

from .. import telemetry, templates
from ..kernel import Message, NAME_RE, OrgError, RESERVED, ROOT, RUNTIME
from ._compat import utcnow


class Retired(NamedTuple):
    addr: str
    refunded: int  # runs of unspent team budget returned to ``refunded_to``
    refunded_to: str | None


class HierarchyMixin:
    """Membership of the agent tree: hire and retire (hierarchy)."""

    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,  # None = the org's default model (DEFAULT_MODEL unless ORG.md sets another)
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
        inputs: list[str] | None = None,
    ) -> str:
        actor = self.require(actor)
        if not NAME_RE.fullmatch(name) or name in RESERVED:
            raise OrgError("name must be lowercase letters, digits and dashes (max 32), and not a reserved word")
        tools = sorted(set(tools or []))
        meta, _ = self.charter(actor)
        if inputs is not None:
            inputs = self._check_inputs(inputs)
        elif actor != ROOT and "read" in tools and not workspace and not self.unconfined_read(meta):
            inputs = []  # a confined hirer never hands down an unconfined `read`: nothing unless it names inputs
        if actor != ROOT:
            if not meta.get("can_hire"):
                raise OrgError("your charter does not allow hiring")
            if len(self.children(actor)) >= int(meta.get("max_children", 5)):
                raise OrgError(f"you already have the maximum of {meta.get('max_children', 5)} direct reports")
            self._check_authority(actor, tools, workspace, inputs)
        addr = self.child_addr(actor, name)
        if self.depth(addr) > int(self.config["max_depth"]):
            raise OrgError(f"the organization is limited to depth {self.config['max_depth']}")
        d = self.dir(addr)
        if d.exists():
            raise OrgError(f"{addr} already exists")
        child_meta = {
            "role": role.strip(),
            "model": model,
            "tools": tools,
            "can_hire": bool(can_hire),
            "max_children": int(max_children),
            "workspace": workspace,
            "inputs": inputs,
            "hired_by": actor,
            "created": utcnow().isoformat(timespec="seconds"),
        }
        child_meta = {k: v for k, v in child_meta.items() if v is not None}
        self.runtime.agent_registry.create(addr, child_meta, templates.charter_body(role, charter))
        self.emit("agent.hire", actor=actor, agent=addr, by=actor, role=telemetry.clip(role.strip()),
                  model=self.model_for(addr), tools=tools)
        return addr

    def retire(self, actor: str, name: str, reason: str) -> str:
        """Remove a direct report and its team; returns the retired address. See :meth:`retire_team`."""
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        """Retire a direct report (short name or full address; root: any agent by full address) and its team.

        Open tasks the team owes the outside are closed as failed, and the team's unspent budget is returned to the
        retired agent's parent as a non-waking runtime note carrying the budget (nothing when the parent is root, who has no
        limit), so budget stays derived from files and is neither destroyed nor minted.
        """
        actor = self.require(actor)
        short = self.norm(name)
        addr = short if "/" in short else self.child_addr(actor, short)
        addr = self.require(addr)
        if addr == ROOT:
            raise OrgError("the root of the organization cannot be retired")
        if actor != ROOT and self.parent(addr) != actor:
            raise OrgError("you can only retire your direct reports")
        team = set(self.subtree(addr))
        for a in team:  # close every task the team owes to the outside world
            for task in self.open_tasks(a):
                if task.sender not in team and self.exists(task.sender):
                    self.deliver(Message(
                        sender=a, to=task.sender, type="result", title=task.title, reply_to=task.id,
                        status="failed", body=f"## Summary\nAgent {a} was retired by {actor}: {reason}",
                    ))
        parent = self.parent(addr)
        # Grants inside the team cancel out, so this is what the parent handed down minus what the team ran.
        refund = max(0, sum(self.budget(a) or 0 for a in team)) if parent != ROOT else 0
        self.runtime.agent_registry.archive(addr, f"{utcnow():%Y%m%dT%H%M%S}")
        if refund:  # after the move: a crash in between loses the refund rather than counting it twice
            self.deliver(Message(
                sender=RUNTIME, to=parent, type="note", budget=refund, wake=False, title=f"Budget returned from {addr}",
                body=templates.notice_budget_returned(addr, refund, actor, reason),
            ))
        self.emit("agent.retire", actor=actor, agent=addr, by=actor, reason=telemetry.clip(reason, telemetry.ERROR_MAX),
                  returned_budget=refund, team=sorted(team))
        return Retired(addr, refund, parent if refund else None)
