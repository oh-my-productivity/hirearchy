"""The parent's acknowledgement of a playbook change (design 9): ``acknowledge_playbook`` writes one quiet note from the owner's parent to the owner.

Retiring, weakening or restoring to a weaker text an item that covers something needs the parent's acknowledgement; the owner then makes the refused
change again with ``acknowledged=<the note's id>`` (the guard of ``RuleItemReviser``). The note is a message, an existing file kind, with one header,
``acknowledges: "{service} {op} {item}[ {text hash}]"``; no state is stored. Each refusal and the reply are constants beside their rule."""

from __future__ import annotations

import hashlib
import re

from ..agents import AgentDirectory
from ..dispatch import MessageSender
from ..kernel import ROOT, Message, OrgError, parent
from ._protocols import OwnerAddresses, PlaybookAcknowledgements
from .api import FEEDBACK_MAX, ServiceCatalog, ServiceEvidence

ACK_NOT_YOURS = "refused: {owner} is not your direct report: only its parent acknowledges a change of its playbook. Nothing was written."
ACK_NO_SERVICE = "refused: {owner} offers no service `{service}`. Its services: {names}. Nothing was written."
ACK_NO_ITEM = "refused: `{service}` of {owner} has no live item {item}. Its items: {ids}. Nothing was written."
ACK_OP = "refused: op is retire or edit (CLI: retire|edit; a restore is acknowledged as edit): {op}. Nothing was written."
ACK_ARGS = (
    'refused: text_hash goes with op="edit" only (CLI: --text-hash): a retire is acknowledged for the item, whatever its text. Nothing was written.'
)
ACK_HASH = (
    'refused: an edit is acknowledged for one new text: pass text_hash="<the 12 hex digits {owner}\'s request named>" (CLI: --text-hash). '
    "Nothing was written."
)
ACK_NOT_NEEDED = (
    "refused: {item} covers no current criterion or confirmed assertion, so {owner} needs no acknowledgement to {op} it. Nothing was written."
)
ACK_WORDS = (
    "refused: an acknowledgement from root records the user's yes: pass words=<their answer, verbatim> (CLI: --words), after they answered yes to "
    "{owner}'s request{length}. Nothing was written."
)
ACK_WORDS_LENGTH = "; words has {n} characters, the limit is {limit}"
ACK_AGENT_WORDS = "refused: words= records the user's own yes, so only root passes it; acknowledge without it. Nothing was written."

ACK_TITLE = "playbook acknowledgement: {op} {item} of {service}"
ACK_BODY = "Acknowledged."  # an agent parent's words
ACK_REPLY = (
    'Acknowledged {op} of {item} ({service}): note {note}. {owner} applies it at its next run by making the refused change again with '
    'acknowledged="{note}".'
)

OPS = ("retire", "edit")
HASH_RE = re.compile(r"[0-9a-f]{12}\Z")
HASH_DIGITS = 12


def text_hash(kind: str, text: str, when: str | None = None) -> str:
    """The first 12 hex digits of the SHA-256, UTF-8, of the text an item would have as it is stored (9.2): a step's ``text`` stripped; a rule's
    ``when + "\\n" + then``, each stripped, with a ``when`` that is absent, empty or ``always`` in any case read as ``always``. It is not the text key
    of the watch: an acknowledgement is for exactly one new text."""
    if kind == "rule":
        condition = (when or "").strip()
        stored = f"{'always' if not condition or condition.lower() == 'always' else condition}\n{text.strip()}"
    else:
        stored = text.strip()
    return hashlib.sha256(stored.encode("utf-8")).hexdigest()[:HASH_DIGITS]


def acknowledge_reply(op: str, item: str, service: str, owner: str, note: str) -> str:
    """The reply to the parent that wrote the acknowledgement ``note``: what it was for and how ``owner`` applies it."""
    return ACK_REPLY.format(op=op, item=item, service=service, owner=owner, note=note)


class RuleAcknowledger(PlaybookAcknowledgements):
    """The owner's parent (root, or the manager that hired it) acknowledges the retire or the edit of one item that covers something. The checks run in
    the order of the design: the owner is the actor's direct report, the service is one it offers, the item is live, the op, the hash, the coverage,
    the words. Nothing is written by a refusal."""

    def __init__(
        self, agents: AgentDirectory, catalog: ServiceCatalog, owners: OwnerAddresses, evidence: ServiceEvidence, sender: MessageSender,
    ) -> None:
        self._agents = agents
        self._catalog = catalog
        self._owners = owners
        self._evidence = evidence
        self._sender = sender

    def acknowledge_playbook(
        self, actor: str, owner: str, service: str, item: str, op: str, *, text_hash: str | None = None, words: str | None = None,
    ) -> Message:
        actor = self._agents.require(actor)
        owner = self._owners.resolve(actor, owner)
        if owner == ROOT or not self._agents.exists(owner) or parent(owner) != actor:
            raise OrgError(ACK_NOT_YOURS.format(owner=owner))
        names = self._catalog.service_names(owner)
        if service not in names:
            raise OrgError(ACK_NO_SERVICE.format(owner=owner, service=service, names=", ".join(names) or "none"))
        item = (item or "").strip().upper()
        live = [i.id for i in self._catalog.read_playbook(owner, service).items or ()]
        if item not in live:
            raise OrgError(ACK_NO_ITEM.format(service=service, owner=owner, item=item, ids=", ".join(live) or "none"))
        op = (op or "").strip().lower()
        if op not in OPS:
            raise OrgError(ACK_OP.format(op=op))
        if op == "retire" and text_hash is not None:
            raise OrgError(ACK_ARGS)
        if op == "edit" and not HASH_RE.match((text_hash or "").strip()):
            raise OrgError(ACK_HASH.format(owner=owner))
        if not any(w.id == item and w.coverage for w in self._evidence.watch(owner, service)):
            raise OrgError(ACK_NOT_NEEDED.format(item=item, owner=owner, op=op))
        spoken = self._words(actor, owner, words)
        header = f"{service} {op} {item}" + (f" {text_hash.strip()}" if op == "edit" and text_hash else "")
        return self._sender.send(
            actor, owner, spoken, type="note", title=ACK_TITLE.format(op=op, item=item, service=service), acknowledges=header,
            source="human" if actor == ROOT else None, wake=False,
        )

    @staticmethod
    def _words(actor: str, owner: str, words: str | None) -> str:
        """The body of the note: the user's yes for root (1 to ``FEEDBACK_MAX`` characters), ``Acknowledged.`` for an agent, who passes none."""
        if actor != ROOT:
            if words is not None:
                raise OrgError(ACK_AGENT_WORDS)
            return ACK_BODY
        spoken = (words or "").strip()
        if not spoken:
            raise OrgError(ACK_WORDS.format(owner=owner, length=""))
        if len(spoken) > FEEDBACK_MAX:
            raise OrgError(ACK_WORDS.format(owner=owner, length=ACK_WORDS_LENGTH.format(n=len(spoken), limit=FEEDBACK_MAX)))
        return spoken
