"""A client asks a direct report for one of its services."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import ROOT, TITLE_MAX, Message, OrgError, clip_line
from ..mail import MailboxReader
from ._criteria import unanswered
from ._lines import criteria_lines
from ._protocols import RequestBodies, ServiceRequests
from .api import (
    BASE_DELIVERED_HEADING, BASE_LATEST_HEADING, JUDGED_BYTES, CaseAllowance, Contract, Criterion, JudgedBase, JudgedVersions, ServiceCatalog,
    ServiceEvidence, ServiceStore, criteria_of,
)

BASES = ("delivered", "latest")
BASE_VALUE = 'refused: base must be "delivered" or "latest": {base}. Nothing was sent.'  # P4-BASE-VALUE
BASE_WHERE = (  # P4-BASE-WHERE
    'refused: base goes only with a rework the user asked for: revises=<an earlier request of this service>, source="human" '
    "(CLI: --revises <task id> --source human). Nothing was sent."
)
NEEDS_BASE = (  # P4-NEEDS-BASE
    "refused: since the delivery the client judged (task {task}, result {result}), relayed rework {ids} (your own reading, not the client's) "
    "changed {paths}. Say which version the user's corrections apply to: base=\"delivered\" (the lead restores the version they judged{commit}, "
    "then applies their corrections) or base=\"latest\" (the relayed changes stay; tell the user) (CLI: --base delivered or --base latest). "
    "Nothing was sent."
)
REQUEST_UNANSWERED = (  # REQUEST-UNANSWERED (clause 2, design 13.1): {more} is "" or " (and {k} more: {R ids})"
    "refused: rejection {assertion} (message {note}) on task {task} of `{service}` has no recorded answer yet{more}, so the next request of "
    "`{service}` waits: every rejection gets the user's answer within one request. Ask the user the one question first: {question}. On yes: "
    'define_service(owner="{owner}", name="{service}", ..., answers="{note}", about=<the id you asked about>, words=<their answer, verbatim>) '
    "(CLI: hirearchy define-service ... --answers, --about, --words). "
    'On no, a one-off or "as it is": feedback(task_id="{task}", verdict="reject", confirms="{note}", criterion=["none"], '
    '["R<j>"] or ["C<k>"], source="human", note=<their answer, verbatim>) '
    "(CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human --note ...). "
    "A rework of that case (revises=) is not held. Nothing was sent."
)
REQUEST_UNREADABLE = (  # REQUEST-UNREADABLE (design 13.1)
    "refused: the record of `{name}` cannot be read ({error}), so the request was not sent. Try again; if it persists, tell the user."
)
_GOAL = {
    "delivered": "The client's corrections apply to the version they judged: see \"## Base\" at the end of this task.",
    "latest": "The client's corrections apply to the current version: see \"## Base\" at the end of this task.",
}
_RELAYED = "(the assistant's own reading, not the client's)"


def _commit(judged: JudgedBase, lead: str) -> str:
    """``lead`` and the first 12 hex digits of the judged commit; nothing without history."""
    return f"{lead}{judged.commit[:12]}" if judged.commit else ""


def _fence(text: str) -> str:
    """A run of backticks one longer than the longest run in ``text`` (at least 3)."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _delivered(judged: JudgedBase) -> str:
    """The base section for ``base="delivered"``: the judged delivery, and the judged text of the paths that changed after it."""
    texts = dict(judged.texts)
    lines = [
        BASE_DELIVERED_HEADING,
        f"The client's corrections apply to the version they judged: the delivery of task {judged.task} (result {judged.result}"
        f"{_commit(judged, ', org-git commit ')}). Relayed rework {', '.join(judged.relayed)} {_RELAYED} changed {', '.join(judged.changed)} "
        "after it. Start from that version: restore each file below to it, then make only the changes this request asks for.",
    ]
    for path in judged.changed:
        if path in texts:
            fence = _fence(texts[path])
            lines += ["", f"### {path}, as the client judged it", fence, texts[path], fence]
        elif judged.commit:
            lines += ["", f"### {path}: not included (the judged texts here are limited to {JUDGED_BYTES} bytes); it is in the organization's git history{_commit(judged, ' at commit ')}."]
        else:
            lines += ["", f"### {path}: not included (no org history)."]
    return "\n".join(lines)


def _latest(judged: JudgedBase) -> str:
    return (
        f"{BASE_LATEST_HEADING}\n"
        f"The client's corrections apply to the current version, which keeps the changes relayed rework {', '.join(judged.relayed)} {_RELAYED} "
        f"made to {', '.join(judged.changed)} after the delivery they judged (task {judged.task}). Keep those changes unless this request says otherwise."
    )


class TextRequestBodies(RequestBodies):
    """The body of a request is its goal, the inputs, the acceptance criteria, the deliverable and the requester's note, as markdown."""

    def body(
        self, contract: Contract, criteria: Sequence[Criterion], given: Mapping[str, str], extra: Sequence[str], note: str,
        base: tuple[str, JudgedBase | None] | None = None,
    ) -> str:
        d = contract.deliverable
        which, judged = base if base is not None else ("", None)
        found = judged is not None and which in _GOAL
        facts = [f"format: {d['format']}"] if d.get("format") else []
        facts += [f"at most {d['max_words']} words"] if d.get("max_words") else []
        facts += [f"path: {d['path']}"] if d.get("path") else []
        names = (str(i["name"]) for i in contract.inputs)
        parts = [
            f"## Goal\nDeliver the service `{contract.name}`: {contract.description}" + (f" {_GOAL[which]}" if found else ""),
            "## Request\n" + ("\n".join(f"- {k}: {given[k]}".replace("\n", "\n  ") for k in names if k in given) or "(no inputs)"),
            "## Acceptance criteria\n" + "\n".join([*(f"- {c.id}: {c.text}" for c in criteria), *(f"- this request only: {x}" for x in extra)]),
            "## Deliverable\n" + str(d.get("description", "")) + (f" ({'; '.join(facts)})" if facts else ""),
        ]
        if note.strip():
            parts.append(f"## Note from the requester\n{note.strip()}")
        if found and judged is not None:  # last: the cut of a long task in the prompt can only reach the tail of the judged text
            parts.append(_delivered(judged) if which == "delivered" else _latest(judged))
        return "\n\n".join(parts)


class RuleServiceRequester(ServiceRequests):
    """The service must be one of a direct report; the inputs must be the contract's; the task goes through the message sender."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, mail: MailboxReader, bodies: RequestBodies, sender: MessageSender,
        judged: JudgedVersions, allowance: CaseAllowance, evidence: ServiceEvidence, store: ServiceStore,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._mail = mail
        self._bodies = bodies
        self._sender = sender
        self._judged = judged
        self._allowance = allowance
        self._evidence = evidence
        self._store = store

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str, note: str,
        extra_acceptance: Sequence[str] | None, budget: int | None, revises: str | None, source: str | None, base: str | None,
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
        if budget is not None and (isinstance(budget, bool) or int(budget) < 1):
            raise OrgError("a request needs a budget of at least 1 run")
        if revises and not any(
            m.id == revises and m.type == "task" and m.to == contract.owner and m.service == service for m in self._mail.sent(actor)
        ):
            raise OrgError(
                f"revises must be the id of an earlier request for `{service}` that you sent to {contract.owner}: {revises}"
            )
        judged = self._base(actor, contract.owner, service, revises, source, base)
        if actor == ROOT and not revises:
            self._answered_first(contract.owner, service)
        if budget is None:
            budget = self._default_budget(actor, contract, revises, source)
        extra = criteria_lines(extra_acceptance, "extra_acceptance", required=False)
        criteria = criteria_of(self._catalog.criteria(contract.owner, service), contract.acceptance)
        body = self._bodies.body(contract, criteria, given, extra, note, base=None if base is None else (base, judged))
        if not title.strip():
            first = next((given[n] for n, i in known.items() if i["required"] and n in given), "")
            title = clip_line(f"{service}: {first}" if first else service, TITLE_MAX)
        return self._sender.send(
            actor, contract.owner, body, type="task", title=title.strip(), budget=int(budget), revises=revises or None,
            source=source, service=service, contract=contract.version, playbook=self._catalog.read_playbook(contract.owner, service).version,
        )

    def _answered_first(self, owner: str, service: str) -> None:
        """Clause 2 (design 13.1): root's new request (not a rework) waits while a human rejection recorded since the service's previous new request
        has no recorded answer (``unanswered``), so that every rejection gets the user's answer within one request. Nothing is due before a first
        new request. The oldest is named, then the others. A record that cannot be read refuses too: a skipped check would let the rejection pass."""
        try:
            previous = max(
                (m.id for m in self._mail.sent(ROOT) if m.type == "task" and m.service == service and m.to == owner and not m.revises), default=None,
            )
            if previous is None:
                return
            waiting = [r for r in unanswered(self._evidence.amendment_basis(owner, service), self._store, owner, service) if r.note > previous]
        except (OrgError, OSError) as error:
            raise OrgError(REQUEST_UNREADABLE.format(name=service, error=error)) from error
        if waiting:
            oldest, others = waiting[0], waiting[1:]
            more = f" (and {len(others)} more: {', '.join(r.assertion for r in others)})" if others else ""
            raise OrgError(REQUEST_UNANSWERED.format(
                assertion=oldest.assertion, note=oldest.note, task=oldest.task, service=service, more=more, question=oldest.question.removesuffix("."), owner=owner,
            ))

    def _default_budget(self, actor: str, contract: Contract, revises: str | None, source: str | None) -> int:
        """The budget of a request that names none: the contract's, except for root's rework the user asked for, which gets what is left of the runs
        the user approved for its case (at most the contract's; 1 when nothing is left: that run is beyond the user's approval, and the reply names it,
        D-E7-2 A1). Never refuses."""
        if not (actor == ROOT and revises and source == "human"):
            return contract.budget  # a fresh request, a relayed rework, an agent's request: unchanged
        try:
            left = self._allowance.left(contract.owner, contract.name, revises)
        except (OrgError, OSError):
            return contract.budget  # a record that cannot be read: the contract's, as before 0a.3
        if left is None:
            return contract.budget
        if left >= 1:
            return min(left, contract.budget)  # what is left, never more than a fresh request gets
        return 1  # nothing left: the minimum a task carries. That run is beyond the user's approval, so the reply names it: its top-up asks for it too, or, when the runs the team holds cover the round, the step says to tell the user (D-E7-2 A1)

    def _base(self, actor: str, owner: str, service: str, revises: str | None, source: str | None, base: str | None) -> JudgedBase | None:
        """What a human rework of ``revises`` starts from (P4): refuses a ``base`` that is not one, or not for this request, and a rework that
        needs a ``base`` and has none; None when no relayed rework changed what the client judged."""
        if base is not None and base not in BASES:
            raise OrgError(BASE_VALUE.format(base=base))
        human = actor == ROOT and bool(revises) and source == "human"
        if base is not None and not human:
            raise OrgError(BASE_WHERE)
        judged = self._judged.base(owner, service, revises) if human and revises else None
        if judged is not None and base is None:
            raise OrgError(NEEDS_BASE.format(
                task=judged.task, result=judged.result, ids=", ".join(judged.relayed), paths=", ".join(judged.changed),
                commit=_commit(judged, ", org-git commit "),
            ))
        return judged
