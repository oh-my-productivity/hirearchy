"""The listing of the services of an agent, with their record, and the totals of a case."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import Message, clip_line
from ..services import Contract, ServiceCatalog
from ._ports import ServicePaths
from .api import CaseHistory, ServiceReports, summarize


class TextServiceReports(ServiceReports):
    """What a client or an owner reads about the services: contract, playbook and record of each, and how much one case has cost."""

    def __init__(self, agents: AgentDirectory, catalog: ServiceCatalog, history: CaseHistory, paths: ServicePaths) -> None:
        self._agents = agents
        self._catalog = catalog
        self._history = history
        self._paths = paths

    def _block(self, c: Contract, *, offered: bool) -> list[str]:
        raise NotImplementedError  # red: C-reflection

    def services_text(self, actor: str) -> str:
        raise NotImplementedError  # red: C-reflection

    def case_total(self, task: Message) -> str:
        raise NotImplementedError  # red: C-reflection
