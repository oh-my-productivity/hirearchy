"""The fields a rework task inherits from the work it belongs to: the service fields of the request it sends back, and the tier of the case."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..dispatch import ReworkContext
from ..kernel import ROOT, RUNTIME, SOURCES, latest_results
from ..mail import MailboxReader
from .api import ServiceCatalog


class ServiceReworkContext(ReworkContext):
    """``service`` and ``contract`` are copied from the revised request; ``playbook`` is the version current now. An agent's rework also gets
    the ``source`` (tier) of the work it does in that case, which its own earlier task does not carry (design 7.6); when that task has no trace, the case is
    the one of the run's batch (0a.3 7.3)."""

    def __init__(self, mail: MailboxReader, agents: AgentDirectory, catalog: ServiceCatalog) -> None:
        self._mail = mail
        self._agents = agents
        self._catalog = catalog

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        task = next((m for m in self._mail.sent(actor) if m.id == revises and m.type == "task"), None)
        if task is None:
            return {}  # not one of actor's tasks: nothing is inherited
        fields: dict[str, object] = {}
        if task.service:  # a rework of a service request keeps its case
            version = self._catalog.read_playbook(task.to, task.service).version if self._agents.exists(task.to) else 0
            fields.update(service=task.service, contract=task.contract, playbook=version)
        trace = task.trace or self._batch_trace(actor)  # a delegation stamped without a trace: the case of the run that revises it (F-E5-7)
        if actor != ROOT and trace:  # the tier of the work actor does in that case; never for root, never without a trace
            tier = self._tier(actor, trace)
            if tier is not None:
                fields["source"] = tier
        return fields

    def _batch_trace(self, actor: str) -> str | None:
        """The one trace of the messages in ``actor``'s run batch (its ``inflight`` box), the stamper's ``batch`` rule; None for none or several."""
        traces = {m.trace for m in self._mail.messages(actor, "inflight") if m.trace}
        return next(iter(traces)) if len(traces) == 1 else None

    def _tier(self, actor: str, trace: str) -> str | None:
        """The ``source`` of the newest task ``actor`` received in the case ``trace`` that it has not answered finally (a ``blocked`` result is not final)."""
        results = latest_results(self._mail.sent(actor))
        for task in reversed(self._mail.received(actor)):
            if task.type != "task" or task.sender == RUNTIME or task.trace != trace:
                continue
            result = results.get(task.id)
            if result is not None and result.status != "blocked":
                continue
            return task.source if task.source in SOURCES else None
        return None
