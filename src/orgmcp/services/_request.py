"""A client asks a direct report for one of its services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import TITLE_MAX, Message, OrgError, clip_line
from ..mail import MailboxReader
from ._lines import criteria_lines
from ._protocols import RequestBodies, ServiceRequests
from .api import Contract, ServiceCatalog


class TextRequestBodies(RequestBodies):
    """The body of a request is its goal, the inputs, the acceptance criteria, the deliverable and the requester's note, as markdown."""

    def body(self, contract: Contract, given: Mapping[str, str], extra: Sequence[str], note: str) -> str:
        raise NotImplementedError


class RuleServiceRequester(ServiceRequests):
    """The service must be one of a direct report; the inputs must be the contract's; the task goes through the message sender."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, mail: MailboxReader, bodies: RequestBodies, sender: MessageSender,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._mail = mail
        self._bodies = bodies
        self._sender = sender

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str, note: str,
        extra_acceptance: Sequence[str] | None, budget: int | None, revises: str | None,
    ) -> Message:
        raise NotImplementedError
