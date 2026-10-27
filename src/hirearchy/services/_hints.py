"""What the ``report`` tool adds for a request for a service, and the client's words in a feedback note."""

from __future__ import annotations

from ..kernel import Message
from .api import FEEDBACK_HEADER, ServiceCatalog, ServiceHints


def client_words(msg: Message) -> str:
    """The client's own words in a feedback note (``""`` for a bare accept); the fixed header is not part of them."""
    body = msg.body.removeprefix(FEEDBACK_HEADER).strip()
    return "" if body == "accepted" else body


NO_PLAYBOOK = (
    'This service has no playbook yet: write v1 now with revise_playbook(op="first", text=...): the steps your team followed, nothing more (no '
    "evidence needed, and only until the client's first verdict or rework; after that, op=\"add\" with the client's evidence). A rule drawn from "
    "your lessons or from a relayed rework is not a step: it needs the client's evidence."
)
WITH_PLAYBOOK = (  # 11: the after-action form is named on every report of a service whose playbook exists
    "Lessons recorded: they are your team's view and are shown before the next request; give them as Expected / Happened / Caught at / Cause / "
    "Prevent, or Near miss. A playbook change rests on the client's evidence (evidence: rejections R<k>, criteria C<k>), not on lessons."
)


class ServiceReportHints(ServiceHints):
    """The owner is reminded to write or change its playbook when it reports a request, unless the contract is locked."""

    def __init__(self, catalog: ServiceCatalog) -> None:
        self._catalog = catalog

    def report_hint(self, actor: str, task: Message, status: str) -> str:
        if not task.service or status not in ("done", "failed"):
            return ""
        contract = self._catalog.read_contract(actor, task.service)
        if contract is None or contract.locked:
            return ""
        if self._catalog.read_playbook(actor, task.service).version == 0:
            return NO_PLAYBOOK
        return WITH_PLAYBOOK

    def feedback_text(self, msg: Message) -> str:
        return client_words(msg)
