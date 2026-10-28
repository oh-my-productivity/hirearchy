"""``LedgerRetroRecords``: ``.runtime/retros.json``, the ledger of the briefs held (design 4.2), over a ``LedgerStore``.

One JSON object ``{"briefs": [record, ...], "asked": [key, ...]}``. A record holds ids and keys only: the id of the brief, its times, who asked for it
(``mcp`` or ``cli``), and for each item its number, kind, key, evidence ids, effect and ``lapsed`` count. The module's pure functions (``parsed``,
``dumped``, ``with_record``) are the rules the fake shares."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from ..kernel import JsonObject, LedgerStore, OrgError, aware
from .api import ASKED_KEPT, RECORDS_KEPT, BriefRecord, RecordedItem, RetroRecords

LEDGER = "retros"  # .runtime/retros.json
PATH = ".runtime/retros.json"

State = tuple[tuple[BriefRecord, ...], tuple[str, ...]]  # the records (oldest first) and the asked keys (oldest first)


def _bad(why: str) -> OrgError:
    return OrgError(f"{PATH} is not a record of briefs ({why})")


def _count(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _bad(f"{what} is not a whole number")
    return value


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise _bad(f"{what} is not text")
    return value


def _texts(value: object, what: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise _bad(f"{what} is not a list of text")
    return tuple(value)


def _time(value: object, what: str) -> datetime:
    text = _text(value, what)
    try:
        return aware(datetime.fromisoformat(text))
    except ValueError as error:
        raise _bad(f"{what} is not a time") from error


def _item(raw: object) -> RecordedItem:
    if not isinstance(raw, dict):
        raise _bad("an item is not an object")
    effect = raw.get("effect", {})
    if not isinstance(effect, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in effect.items()):
        raise _bad("an effect is not an object of text")
    return RecordedItem(
        _count(raw.get("n"), "an item's n"), _text(raw.get("kind"), "an item's kind"), _text(raw.get("key"), "an item's key"),
        _texts(raw.get("evidence"), "an item's evidence"), dict(effect), _count(raw.get("lapsed", 0), "an item's lapsed"),
    )


def _record(raw: object) -> BriefRecord:
    if not isinstance(raw, dict):
        raise _bad("a brief is not an object")
    items = raw.get("items", [])
    if not isinstance(items, list):
        raise _bad("items is not a list")
    since = raw.get("since")
    return BriefRecord(
        _text(raw.get("id"), "a brief's id"), _time(raw.get("at"), "a brief's at"), None if since is None else _time(since, "a brief's since"),
        _text(raw.get("by", ""), "a brief's by"), tuple(_item(i) for i in items), _texts(raw.get("held_back"), "held_back"),
    )


def parsed(data: Mapping[str, object]) -> State:
    """The records and the asked keys of a ledger's JSON; ``OrgError`` when it is no ledger of briefs. An empty ledger holds nothing."""
    briefs = data.get("briefs", [])
    if not isinstance(briefs, list):
        raise _bad("briefs is not a list")
    return tuple(_record(b) for b in briefs), _texts(data.get("asked"), "asked")


def _stamp(when: datetime | None) -> str | None:
    return None if when is None else aware(when).isoformat()


def dumped(briefs: Sequence[BriefRecord], asked: Sequence[str]) -> JsonObject:
    """The JSON of a ledger holding these records and keys."""
    return {
        "briefs": [
            {
                "id": b.id, "at": _stamp(b.at), "since": _stamp(b.since), "by": b.by,
                "items": [
                    {"n": i.n, "kind": i.kind, "key": i.key, "evidence": list(i.evidence), "effect": dict(i.effect), "lapsed": i.lapsed} for i in b.items
                ],
                "held_back": list(b.held_back),
            }
            for b in briefs
        ],
        "asked": list(asked),
    }


def with_record(state: State, record: BriefRecord) -> State:
    """``state`` with ``record`` added: the newest ``RECORDS_KEPT`` records, and the keys of its items at the newest end of the asked keys (a key
    offered again moves there), the newest ``ASKED_KEPT``."""
    briefs, asked = state
    keys = list(asked)
    for item in record.items:
        if item.key in keys:
            keys.remove(item.key)
        keys.append(item.key)
    return (*briefs, record)[-RECORDS_KEPT:], tuple(keys[-ASKED_KEPT:])


class LedgerRetroRecords(RetroRecords):
    def __init__(self, ledgers: LedgerStore) -> None:
        self._ledgers = ledgers

    def _state(self) -> State:
        return parsed(self._ledgers.read(LEDGER))

    def last(self) -> BriefRecord | None:
        briefs = self._state()[0]
        return briefs[-1] if briefs else None

    def records(self) -> tuple[BriefRecord, ...]:
        return self._state()[0]

    def asked(self) -> frozenset[str]:
        return frozenset(self._state()[1])

    def append(self, record: BriefRecord) -> None:
        try:
            state = self._state()
        except OrgError:
            state = ((), ())  # a ledger that is none replaces itself: the brief that is recorded now starts the record again
        briefs, asked = with_record(state, record)
        try:
            self._ledgers.write(LEDGER, dumped(briefs, asked))
        except OSError as error:
            raise OrgError(f"{PATH} cannot be written: {error}") from error
