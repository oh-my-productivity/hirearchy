"""Creating a direct report (moved from ``Org.hire``)."""

from __future__ import annotations

from collections.abc import Sequence

from ..access import AccessScopes, AuthorityPolicy, ModelResolver
from ..agents import AgentDirectory, AgentRegistry, CharterReader
from ..kernel import Clock, EventSink
from ..settings import OrgSettings
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
    ) -> str:
        raise NotImplementedError("B-hierarchy")
