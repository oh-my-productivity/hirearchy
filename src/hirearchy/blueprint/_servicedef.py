"""``PlaybookServiceDefiner``: the services of a blueprint, defined for its top-level agent."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from ..kernel import ROOT
from ..services import ContractNormalizer, ServiceCommands
from ._protocols import BudgetPlanning, PlaybookWriting, ServiceDefining
from ._shapes import Built
from ._view import criterion_source, needs_of, s, services_of, svc_criteria, svc_criteria_entries, svc_deliverable
from .api import Agent


class PlaybookServiceDefiner(ServiceDefining):
    def __init__(
        self, commands: ServiceCommands, normalizer: ContractNormalizer, playbooks: PlaybookWriting, budgets: BudgetPlanning,
    ) -> None:
        self._commands = commands
        self._normalizer = normalizer
        self._playbooks = playbooks
        self._budgets = budgets

    def define(self, bp: Mapping[str, object], agents: Sequence[Agent], built: Built) -> None:
        top = agents[0]
        budgets = self._budgets.service_budgets(bp, agents)
        words = s(needs_of(bp).get("elicitation"))
        for sv in services_of(bp):
            name = s(sv.get("name"))
            d = dict(self._normalizer.deliverable(svc_deliverable(sv)))
            if d.get("path"):
                d["path"] = os.path.expanduser(str(d["path"]))
            sources = [criterion_source(entry) for entry in svc_criteria_entries(sv)]
            raw = sv.get("playbook")
            playbook = raw.strip() if isinstance(raw, str) and raw.strip() else self._playbooks.default_playbook(top, agents, sv, budgets[name])
            self._commands.define_service(
                ROOT, top.addr, name, description=s(sv.get("description")), inputs=self._normalizer.inputs(sv.get("inputs")),
                acceptance=svc_criteria(sv), deliverable=d, budget=budgets[name], playbook=playbook, locked=sv.get("locked") is True,
                sources=sources if any(sources) else None, elicitation=words or None,
            )
            built.defined.append(name)
