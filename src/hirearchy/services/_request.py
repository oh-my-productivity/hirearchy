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
        d = contract.deliverable
        facts = [f"format: {d['format']}"] if d.get("format") else []
        facts += [f"at most {d['max_words']} words"] if d.get("max_words") else []
        facts += [f"path: {d['path']}"] if d.get("path") else []
        names = (str(i["name"]) for i in contract.inputs)
        parts = [
            f"## Goal\nDeliver the service `{contract.name}`: {contract.description}",
            "## Request\n" + ("\n".join(f"- {k}: {given[k]}".replace("\n", "\n  ") for k in names if k in given) or "(no inputs)"),
            "## Acceptance criteria\n" + "\n".join(f"- {c}" for c in [*contract.acceptance, *extra]),
            "## Deliverable\n" + str(d.get("description", "")) + (f" ({'; '.join(facts)})" if facts else ""),
        ]
        if note.strip():
            parts.append(f"## Note from the requester\n{note.strip()}")
        return "\n\n".join(parts)


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
        extra_acceptance: Sequence[str] | None, budget: int | None, revises: str | None, source: str | None,
    ) -> Message:
        actor = self._agents.require(actor)
        available = self._catalog.requestable_services(actor)
        contract = next((c for c in available if c.name == service), None)
        if contract is None:
            listing = ", ".join(f"{c.name} (offered by {c.owner})" for c in available) or "none"
            raise OrgError(
                f"no service `{service}` among your direct reports. Services you can request: {listing}. "
                "A parent defines one with define_service."
            )
        given = {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in (inputs or {}).items()}
        known = {str(i["name"]): i for i in contract.inputs}
        unknown = [k for k in given if k not in known]
        if unknown:
            raise OrgError(
                f"unknown input(s) for `{service}`: {', '.join(unknown)}. Its inputs: {', '.join(known) or 'none'}."
            )
        missing = [n for n, i in known.items() if i["required"] and not given.get(n)]
        if missing:
            raise OrgError(f"missing required input(s) for `{service}`: {', '.join(missing)}. Pass them in `inputs`.")
        given = {k: v for k, v in given.items() if v}
        if budget is None:
            budget = contract.budget
        if isinstance(budget, bool) or int(budget) < 1:
            raise OrgError("a request needs a budget of at least 1 run")
        if revises and not any(
            m.id == revises and m.type == "task" and m.to == contract.owner and m.service == service for m in self._mail.sent(actor)
        ):
            raise OrgError(
                f"revises must be the id of an earlier request for `{service}` that you sent to {contract.owner}: {revises}"
            )
        extra = criteria_lines(extra_acceptance, "extra_acceptance", required=False)
        body = self._bodies.body(contract, given, extra, note)
        if not title.strip():
            first = next((given[n] for n, i in known.items() if i["required"] and n in given), "")
            title = clip_line(f"{service}: {first}" if first else service, TITLE_MAX)
        return self._sender.send(
            actor, contract.owner, body, type="task", title=title.strip(), budget=int(budget), revises=revises or None,
            source=source, service=service, contract=contract.version, playbook=self._catalog.read_playbook(contract.owner, service).version,
        )
