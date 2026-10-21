"""What the ``report`` tool adds for a request for a service, and the client's words in a feedback note."""

from __future__ import annotations

from ..kernel import Message
from .api import FEEDBACK_HEADER, ServiceCatalog, ServiceHints


def client_words(msg: Message) -> str:
    """The client's own words in a feedback note (``""`` for a bare accept); the fixed header is not part of them."""
    body = msg.body.removeprefix(FEEDBACK_HEADER).strip()
    return "" if body == "accepted" else body


class ServiceReportHints(ServiceHints):
    """The owner is reminded to write or revise its playbook when it reports a request, unless the contract is locked."""

    def __init__(self, catalog: ServiceCatalog) -> None:
        self._catalog = catalog

    def report_hint(self, actor: str, task: Message, status: str) -> str:
        if not task.service or status not in ("done", "failed"):
            return ""
        contract = self._catalog.read_contract(actor, task.service)
        if contract is None or contract.locked:
            return ""
        if self._catalog.read_playbook(actor, task.service).version == 0:
            return (
                "This service has no playbook yet: write v1 now with revise_playbook: the steps your team followed, nothing more (the first "
                "version needs no evidence: evidence=[]). A rule drawn from your lessons or from a relayed rework is not a step: it needs the "
                "client's evidence in a later revision."
            )
        return (
            "Lessons recorded: they are your team's view and are shown before the next request. A playbook revision rests on the client's "
            "evidence (evidence: rejections R<k>, criteria C<k>), not on lessons."
        )

    def feedback_text(self, msg: Message) -> str:
        return client_words(msg)
