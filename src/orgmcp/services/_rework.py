"""The service fields a rework task inherits from the request it sends back."""

from __future__ import annotations

from collections.abc import Mapping

from ..agents import AgentDirectory
from ..dispatch import ReworkContext
from ..mail import MailboxReader
from .api import ServiceCatalog


class ServiceReworkContext(ReworkContext):
    """``service`` and ``contract`` are copied from the revised request; ``playbook`` is the version current now."""

    def __init__(self, mail: MailboxReader, agents: AgentDirectory, catalog: ServiceCatalog) -> None:
        self._mail = mail
        self._agents = agents
        self._catalog = catalog

    def fields_for(self, actor: str, revises: str) -> Mapping[str, object]:
        task = next((m for m in self._mail.sent(actor) if m.id == revises and m.type == "task"), None)
        if task is None or not task.service:
            return {}
        version = self._catalog.read_playbook(task.to, task.service).version if self._agents.exists(task.to) else 0
        return {"service": task.service, "contract": task.contract, "playbook": version}
