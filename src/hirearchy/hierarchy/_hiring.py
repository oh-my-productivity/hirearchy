"""Creating a direct report (moved from ``Org.hire``)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import SupportsInt, cast

from ..access import AccessScopes, AuthorityPolicy, ModelResolver, children_limit
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import NAME_RE, RESERVED, ROOT, Clock, EventSink, OrgError, child_addr, clip, depth
from ..settings import OrgSettings, config_default_model, model_floor_problem, readable_config
from ..templates import DocumentTemplates
from ._ports import AgentSlots
from .api import Hiring


class RuleHiring(Hiring):
    """Applies the rules of hiring, then has the registry write the new agent."""

    def __init__(
        self,
        agents: AgentDirectory,
        charters: CharterReader,
        registry: AgentRegistry,
        slots: AgentSlots,
        settings: OrgSettings,
        templates: DocumentTemplates,
        scopes: AccessScopes,
        authority: AuthorityPolicy,
        models: ModelResolver,
        clock: Clock,
        events: EventSink,
    ) -> None:
        self._agents = agents
        self._charters = charters
        self._registry = registry
        self._slots = slots
        self._settings = settings
        self._templates = templates
        self._scopes = scopes
        self._authority = authority
        self._models = models
        self._clock = clock
        self._events = events

    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,
        tools: Sequence[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
        inputs: Sequence[str] | None = None,
        approved: bool = False,
        kind: str | None = None,
        approved_in: str | None = None,
    ) -> str:
        actor = self._agents.require(actor)
        if not NAME_RE.fullmatch(name) or name in RESERVED:
            raise OrgError("name must be lowercase letters, digits and dashes (max 32), and not a reserved word")
        cfg = readable_config(self._settings)  # one read for the floor and the depth; ORG.md that does not parse is refused in plain words
        given = (model or "").strip()
        problem = model_floor_problem(cfg, given or config_default_model(cfg))  # the effective model: docs/design/org-agent-model-floor.md 3
        if problem is not None:
            raise OrgError(problem if given else f"default_model: {problem}")
        limit = children_limit(max_children)  # A3, for every hirer
        if not can_hire:
            limit = 0  # the limit means nothing without the right
        tools = sorted(set(tools or []))
        meta, _ = self._charters.charter(actor)
        if inputs is not None:
            inputs = self._authority.check_inputs(inputs)
        elif actor != ROOT and "read" in tools and not workspace and not self._scopes.unconfined_read(meta):
            inputs = []  # a confined hirer never hands down an unconfined `read`: nothing unless it names inputs
        if actor != ROOT:
            if not meta.get("can_hire"):
                raise OrgError("your charter does not allow hiring")
            if len(self._agents.children(actor)) >= int(cast("SupportsInt | str", meta.get("max_children", 5))):
                raise OrgError(f"you already have the maximum of {meta.get('max_children', 5)} direct reports")
            self._authority.check_authority(actor, tools, workspace, inputs)
            if not approved:
                self._authority.check_grant(actor, grants_hire=bool(can_hire), max_children=limit)
        addr = child_addr(actor, name)
        max_depth = cfg["max_depth"]
        if depth(addr) > int(cast("SupportsInt | str", max_depth)):
            raise OrgError(f"the organization is limited to depth {max_depth}")
        if self._slots.occupied(addr):
            raise OrgError(f"{addr} already exists")
        child_meta = {
            "role": role.strip(),
            "model": model,
            "tools": tools,
            "can_hire": bool(can_hire),
            "max_children": limit,
            "workspace": workspace,
            "inputs": inputs,
            "hired_by": actor,
            "created": self._clock.now().isoformat(timespec="seconds"),
            "kind": kind,
            "approved_in": approved_in,
        }
        child_meta = {k: v for k, v in child_meta.items() if v is not None}
        self._registry.create(addr, child_meta, self._templates.charter_body(role, charter))
        self._events.emit("agent.hire", actor=actor, agent=addr, by=actor, role=clip(role.strip()),
                          model=self._models.model_for(addr), tools=tools)
        return addr
