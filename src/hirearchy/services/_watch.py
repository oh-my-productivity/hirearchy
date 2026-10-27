"""The watch settler (design 8.5): two related rejections retire the watched text of an item, and the runtime, as the ``services`` single writer, writes
the version that does it. The watch itself is derived by ``reflection`` and reached through ``ServiceEvidence.watch``; this module only acts on what it
says is due, and tells the owner and the client (8.3)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from ..delivery import MessageDelivery
from ..kernel import ROOT, OrgError, parent
from ._items import RUNTIME_MIGRATION, RUNTIME_WATCH, SPLITTERS, Splitter, and_ids, canonical_why, checked_body, item_extra, migrate_body, repair_of, without
from ._ops import item_tokens
from ._protocols import PlaybookWriter, SettleReport, WatchSettlement
from .api import ItemWatch, Playbook, PlaybookItem, ServiceCatalog, ServiceEvidence

__all__ = ["RuleWatchSettler", "SettleReport"]  # SettleReport is defined beside the Protocol it answers (_protocols), as 8.5 names it here

WARNING_TITLE = "playbook item {id} of {service}: warning"
WARNING_BODY = (  # to the owner, on the first related rejection (8.3)
    "Rejection {rejection} (case {case}) is about {subjects}, which {id} cites. One more related rejection retires {id}{restores}. "
    "Follow the contract where they differ."
)
WARNING_RESTORES = " and restores the text of v{k}"
RETIRE_TITLE = "playbook of {service}: the watch retired {id}"
RETIRE_BODY = (  # to the owner and the client, on the watch retire: ids only, never the item's words (5.2)
    "Rejections {rejections} are about {subjects}, which {id} cited, so the runtime retired it{restored} (playbook v{n}). "
    "The client's verdicts decide this; no acknowledgement is needed."
)
RETIRE_RESTORED = " and restored the text of v{k}"
RETIRE_REASON = "the client rejected {rejections}, which are about {subjects}"
REPAIR_TITLE = "playbook of {service}: v{n} (items)"
NO_IDS = "nothing"  # the ids an item cites, when it cites none
CASE_UNKNOWN = "unknown"
_CITED = re.compile(r"\b[CR]\d+\b")


def _number(item_id: str) -> int:
    return int(item_id[1:]) if item_id[1:].isdigit() else 0


def _cited(item: PlaybookItem) -> str:
    """The ids an item cites, for the notes: its ``why`` entry, else the ``C`` and ``R`` ids in its words."""
    ids = canonical_why(item.why) or tuple(dict.fromkeys(_CITED.findall(f"{item.text} {item.when}")))
    return ", ".join(ids) or NO_IDS


class RuleWatchSettler(WatchSettlement):
    """Retires the items the watch says are due (2 or more related rejections) and warns the owner of the first one (8.5). Exempt from the guard of
    section 9 and from the contract's lock: the client's verdicts are the authority, and the lock stops the owner's ops, not them."""

    def __init__(
        self, catalog: ServiceCatalog, evidence: ServiceEvidence, playbooks: PlaybookWriter, delivery: MessageDelivery,
        *, splitters: Sequence[Splitter] = SPLITTERS,
    ) -> None:
        self._catalog = catalog
        self._evidence = evidence
        self._playbooks = playbooks
        self._delivery = delivery
        self._splitters = splitters

    def settle(self, owner: str, service: str, before: Sequence[ItemWatch] | None, *, strict: bool = False) -> SettleReport:
        try:
            after = self._evidence.watch(owner, service)
        except (OrgError, OSError) as error:  # a read that fails writes nothing: the next trigger derives again
            return SettleReport(failed=(("", str(error)),))
        client = parent(owner) or ROOT
        failed: list[tuple[str, str]] = []
        due = self._due(after)
        if due and self._repaired(owner, service, client, due, strict, failed):
            try:
                after = self._evidence.watch(owner, service)
            except (OrgError, OSError) as error:
                return SettleReport(failed=(*failed, ("", str(error))))
            due, before = self._due(after), None  # the repair gave the lines new ids: the old ones say nothing about them
        elif due and failed:
            return SettleReport(failed=tuple(failed))
        done: list[tuple[ItemWatch, PlaybookItem, int, int]] = []  # the watch, the item as it was, the version written, the version restored (0: none)
        for w in due:
            try:
                found = self._retire(owner, service, w)
            except (OrgError, OSError) as error:  # PlaybookRace is an OrgError
                if strict:
                    raise
                failed.append((w.id, str(error)))
                continue
            if found is not None:
                done.append((w, *found))
        for w, old, n, k in done:
            self._tell_retire(owner, service, client, w, old, n, k, strict, failed)
        warned = self._warn(owner, service, after, before, {w.id for w, *_ in done}, strict, failed)
        return SettleReport(tuple(w.id for w, *_ in done), tuple(warned), tuple(failed))

    @staticmethod
    def _due(watch: Sequence[ItemWatch]) -> list[ItemWatch]:
        return sorted((w for w in watch if w.retire_due), key=lambda w: _number(w.id))

    # ------------------------------------------------------------------------------------------------------ the repair (4.4)

    def _repaired(self, owner: str, service: str, client: str, due: Sequence[ItemWatch], strict: bool, failed: list[tuple[str, str]]) -> bool:
        """The repair migration of a body that no longer parses, written before the retire (it carries the watches, by text key): True when written."""
        try:
            current = self._catalog.read_playbook(owner, service)
            if not (current.version and current.parse_error):
                return False
            fix = repair_of(migrate_body(current.body, splitters=self._splitters), current.version, current.items_max, current.parse_error)
            extra = item_extra(fix.items, fix.top, "migrate", admitted="migrate")
            body = checked_body(fix.items, fix.sections, extra)
            self._playbooks.write(owner, service, current.version + 1, body, RUNTIME_MIGRATION, fix.reason, current.version, extra)
        except (OrgError, OSError) as error:
            if strict:
                raise
            failed.extend((w.id, str(error)) for w in due)
            return False
        self._tell(client, REPAIR_TITLE.format(service=service, n=current.version + 1), fix.alone, "", strict, failed)
        return True

    # ------------------------------------------------------------------------------------------------------ the retire (8.5)

    def _retire(self, owner: str, service: str, w: ItemWatch) -> tuple[PlaybookItem, int, int] | None:
        """Write the next version without the watched text of ``w``, with the text before the watch back in its place when there is one; None when
        the item is no longer live in the watched text (another writer retired it, or a gated change restarted its watch: the next derivation
        handles it). Returns the item as it was, the version written and the version whose text came back (0: none)."""
        current = self._catalog.read_playbook(owner, service)
        live = next((i for i in current.items or () if i.id == w.id), None)
        versions = self._catalog.playbook_versions(owner, service)
        watched = self._watched(versions, w)
        if live is None or watched is None or item_tokens(live) != item_tokens(watched):
            return None
        previous = self._before(versions, w, watched)
        items, sections = current.items or (), current.sections
        if previous is None:
            items, sections = without(items, sections, live)
            k = 0
        else:
            k, text = previous
            items = tuple(replace(text, section=live.section) if i.id == live.id else i for i in items)
        extra = item_extra(
            items, current.items_max, "watch", admitted="watch", item=w.id, related=list(w.related), restores=k,
        )
        body = checked_body(items, sections, extra)  # the round trip, asserted before the write
        reason = RETIRE_REASON.format(rejections=and_ids(w.related), subjects=_cited(live))
        self._playbooks.write(owner, service, current.version + 1, body, RUNTIME_WATCH, reason, current.version, extra)
        return live, current.version + 1, k

    @staticmethod
    def _watched(versions: Sequence[Playbook], w: ItemWatch) -> PlaybookItem | None:
        """The item as the watched change gave it: in the first version at or after ``w.text_version`` that holds its id (a repair gives a watched
        text a new id, in a later version)."""
        for v in versions:
            if v.items is not None and v.version >= w.text_version:
                found = next((i for i in v.items if i.id == w.id), None)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _before(versions: Sequence[Playbook], w: ItemWatch, watched: PlaybookItem) -> tuple[int, PlaybookItem] | None:
        """The text the item had before its watch (the version it is in and the item), when the watch retire puts it back: its text in the last
        parseable version revised before the watch start, of the same kind and with other text tokens than the watched text (R3-F8: a restore that
        brought exactly that text back leaves nothing to restore). None for an item that was not live there."""
        if w.watch_start is None:
            return None
        earlier = [v for v in versions if v.items is not None and v.revised is not None and v.revised < w.watch_start]
        if not earlier:
            return None
        v = earlier[-1]
        found = next((i for i in v.items or () if i.id == w.id), None)
        if found is None or found.kind != watched.kind or item_tokens(found) == item_tokens(watched):
            return None
        return v.version, found

    # ------------------------------------------------------------------------------------------------------ the notes (8.3)

    def _tell_retire(
        self, owner: str, service: str, client: str, w: ItemWatch, old: PlaybookItem, n: int, k: int, strict: bool, failed: list[tuple[str, str]],
    ) -> None:
        """The quiet note of a retire to the owner and to the client (the same sentence: ids only, so root's note never carries the item's words)."""
        body = RETIRE_BODY.format(
            rejections=and_ids(w.related), subjects=_cited(old), id=w.id, n=n, restored=RETIRE_RESTORED.format(k=k) if k else "",
        )
        title = RETIRE_TITLE.format(service=service, id=w.id)
        for to in dict.fromkeys((owner, client)):
            self._tell(to, title, body, w.id, strict, failed)

    def _warn(
        self, owner: str, service: str, after: Sequence[ItemWatch], before: Sequence[ItemWatch] | None, retired: set[str], strict: bool,
        failed: list[tuple[str, str]],
    ) -> list[str]:
        """The quiet note to the owner for each item whose related count went from 0 (in ``before``) to exactly 1; the ids warned."""
        if before is None:
            return []
        known = {w.id: w for w in before}
        fresh = [w for w in after if w.state == "warning" and len(w.related) == 1 and w.id not in retired and not (w.id in known and known[w.id].related)]
        if not fresh:
            return []
        try:
            current = self._catalog.read_playbook(owner, service)
            versions = self._catalog.playbook_versions(owner, service)
        except (OrgError, OSError) as error:
            if strict:
                raise
            failed.extend((w.id, str(error)) for w in fresh)
            return []
        warned: list[str] = []
        for w in sorted(fresh, key=lambda w: _number(w.id)):
            live = next((i for i in current.items or () if i.id == w.id), None)
            watched = self._watched(versions, w)
            if live is None or watched is None:
                continue
            previous = self._before(versions, w, watched)
            body = WARNING_BODY.format(
                rejection=w.related[0], case=self._case(owner, service, w.related[0]), subjects=_cited(live), id=w.id,
                restores=WARNING_RESTORES.format(k=previous[0]) if previous else "",
            )
            if self._tell(owner, WARNING_TITLE.format(id=w.id, service=service), body, w.id, strict, failed):
                warned.append(w.id)
        return warned

    def _case(self, owner: str, service: str, rejection: str) -> str:
        """The case of rejection ``rejection`` (the id of its first task); ``unknown`` when the record cannot be read or does not hold it."""
        try:
            found = next((r for r in self._evidence.amendment_basis(owner, service).rejections if r.assertion == rejection), None)
        except (OrgError, OSError):
            return CASE_UNKNOWN
        return (found.case or found.task) if found is not None else CASE_UNKNOWN

    def _tell(self, to: str, title: str, body: str, item: str, strict: bool, failed: list[tuple[str, str]]) -> bool:
        """A quiet note; a note that cannot be delivered is recorded as failed (never raised) unless the caller is strict. True when delivered."""
        try:
            self._delivery.notify(to, title, body, wake=False)
        except (OrgError, OSError) as error:
            if strict:
                raise
            failed.append((item, f"note to {to}: {error}"))
            return False
        return True
