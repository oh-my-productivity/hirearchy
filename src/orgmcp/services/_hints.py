"""What the ``report`` tool adds for a request for a service, and the client's words in a feedback note."""

from __future__ import annotations

from ..kernel import Message
from .api import FEEDBACK_HEADER, ServiceCatalog, ServiceHints


def client_words(msg: Message) -> str:
    """The client's own words in a feedback note (``""`` for a bare accept); the fixed header is not part of them."""
    raise NotImplementedError


class ServiceReportHints(ServiceHints):
    """The owner is reminded to write or revise its playbook when it reports a request, unless the contract is locked."""

    def __init__(self, catalog: ServiceCatalog) -> None:
        self._catalog = catalog

    def report_hint(self, actor: str, task: Message, status: str) -> str:
        raise NotImplementedError

    def feedback_text(self, msg: Message) -> str:
        raise NotImplementedError
