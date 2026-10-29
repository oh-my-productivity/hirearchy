"""``FileRetroBriefs``: the retro brief of the files (design 4.2, 4.8), recorded or shown again.

``brief(since=None)`` derives the brief, then decides: it is recorded as B(n+1) when a human verdict was created after the last brief (or there is none), and the last brief is
shown again, recorded nowhere, otherwise; ``brief(since=...)`` is a look-back, recorded nowhere. The brief is derived first, so a ledger that cannot be written still returns it, with
the line of 4.8. The class sends no message and writes nothing but the ledger."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from ..kernel import Clock, EventSink, OrgError
from ..settings import OrgSettings
from ._changes import changes_of
from ._effect import evaluate, listed
from ._facts import Facts
from ._items import Selection, fates, select, taken_by, to_record
from ._ports import BriefSources
from ._readings import (
    d1_said, d2_passed, d3_unlinked, d4_alarms, d5_repeated, d6_health, d7_held, d8_changes, d9_criteria, d10_proposals, d11_playbooks, d12_spend, d13_last,
    d14_held,
)
from ._shapes import groups
from ._signals import REF, answer_items, cause_items, checker_items, clarify_items, grown_estimate, idle_items, service_items
from ._texts import day
from ._views import EffectFacts, Fate, ServiceFailures, TakenFix
from .api import Brief, BriefRecord, Item, RetroBriefs, RetroRecords, RetroThresholds, Section, retro_thresholds

UNREADABLE = "The record of earlier briefs cannot be read ({error}): this brief counts every verdict as new and lapses nothing."
NOT_RECORDED = "This brief was not recorded ({error}): the next one repeats it."
FUTURE = "refused: since is in the future ({since}). Nothing was read."


def _with_taken(failures: tuple[ServiceFailures, ...], records: tuple[BriefRecord, ...], effects: EffectFacts) -> tuple[ServiceFailures, ...]:
    """The services with the instructions already taken (the ``checker-fix`` items of the records whose effect is in the files) and the case in which their class recurred."""
    out = []
    for f in failures:
        taken: list[TakenFix] = []
        for record in records:
            for item in record.items:
                parts = item.key.split("|", 3)
                if item.kind != "checker-fix" or len(parts) != 4 or parts[1] != f.service or not taken_by(item, effects):
                    continue
                again = next((c.case for c in f.window if c.when is not None and c.when > record.at and any(parts[3] in k for k in c.classes)), "")
                taken.append(TakenFix(parts[2], parts[3], f"{record.id}.{item.n}", again))
        out.append(replace(f, taken=tuple(taken)))
    return tuple(out)


def _candidates(facts: Facts, th: RetroThresholds, taken: frozenset[str], records: tuple[BriefRecord, ...]) -> tuple[list[Item], tuple[str, ...]]:
    """Every candidate of every signal, and the D6 lines the idle signal adds."""
    idle, d6_lines = idle_items(facts.flags, facts.last_checks, facts.owners)
    checkers = checker_items(_with_taken(facts.failures, records, facts.effects), th)
    adding = {i.effect.get("owner") for i in checkers if i.kind == "checker-add"}
    grown = {f.owner: grown_estimate(f.owner_facts) for f in facts.failures if f.owner in adding}  # a service the same brief offers is budgeted for the team the checker leaves
    found = [
        *service_items(groups(facts.one_offs, th.shape_overlap), facts.offers, taken, facts.estimates, th, grown), *checkers, *idle,
        *clarify_items(facts.sourced, th), *cause_items(facts.passed), *answer_items(facts.said),
    ]
    return found, d6_lines


def _stamped(item: Item, brief_id: str) -> Item:
    """The item with its id written where its calls carry ``B{n}.{k}``."""
    ref = f"{brief_id}.{item.n}"
    return replace(item, blueprint=item.blueprint.replace(REF, ref), revert_blueprint=item.revert_blueprint.replace(REF, ref))


class FileRetroBriefs(RetroBriefs):
    def __init__(self, sources: BriefSources, records: RetroRecords, settings: OrgSettings, sink: EventSink, clock: Clock, by: str = "mcp") -> None:
        self._sources = sources
        self._records = records
        self._settings = settings
        self._sink = sink
        self._clock = clock
        self._by = by

    def brief(self, *, since: datetime | None = None) -> Brief:
        now = self._clock.now()
        if since is not None and since > now:
            raise OrgError(FUTURE.format(since=day(since)))
        th, notes = retro_thresholds(self._settings.config())
        notes_out = list(notes)
        recs: tuple[BriefRecord, ...] = ()
        asked: frozenset[str] = frozenset()
        try:
            recs, asked = self._records.records(), self._records.asked()
        except OrgError as error:
            notes_out.insert(0, UNREADABLE.format(error=error))
            self._sink.emit("retro.ledger_unreadable", error=str(error))
        last = recs[-1] if recs else None
        look_back = since is not None
        started = self._sources.started()
        new = self._sources.new_verdicts(last.at if last is not None else None)
        shown_again = not look_back and last is not None and new < 1
        window = since if look_back else last.since if shown_again and last is not None else (last.at if last is not None else started)
        facts = self._sources.read(window, last.at if last is not None else None)
        taken_keys = frozenset(i.key for i in last.items if taken_by(i, facts.effects)) if last is not None else frozenset()
        found, d6_lines = _candidates(facts, th, taken_keys, recs)
        picked = select(found, recs, asked, taken_keys, th.items)
        record = not look_back and not shown_again
        number = int(last.id[1:]) + 1 if last is not None and last.id[1:].isdigit() else 1
        brief_id = "look-back" if look_back else last.id if shown_again and last is not None else f"B{number}"
        items, held = self._items(picked, found, last, taken_keys, facts, shown_again, brief_id)
        sections = self._sections(facts, th, window, recs, last, record, held, d6_lines, picked)
        recorded = False
        if record:
            entry = BriefRecord(brief_id, now, window, self._by, to_record(items, recs, taken_keys), tuple(c.key for c in held))
            try:
                self._records.append(entry)
                recorded = True
            except OrgError as error:
                notes_out.append(NOT_RECORDED.format(error=error))
                self._sink.emit("retro.record_failed", error=str(error))
        words = self._words(look_back, shown_again, window, started, last)
        return Brief(brief_id, now, window, words, facts.verdicts, facts.cases, sections, items, held, tuple(notes_out), recorded, day(last.at) if shown_again and last else "")

    @staticmethod
    def _words(look_back: bool, shown_again: bool, window: datetime | None, started: datetime | None, last: BriefRecord | None) -> str:
        if look_back:
            return f"since {day(window)} (a look-back; not recorded)"
        if last is not None and not shown_again:
            return f"since the last brief, {day(last.at)}"
        if window is None:
            return "since the organization started"
        return f"since the organization started, {day(window)}" if window == started else f"since {day(window)}"

    @staticmethod
    def _items(
        picked: Selection, found: list[Item], last: BriefRecord | None, taken_keys: frozenset[str], facts: Facts, shown_again: bool, brief_id: str,
    ) -> tuple[tuple[Item, ...], tuple[Item, ...]]:
        if shown_again and last is not None:
            fresh = {c.key: c for c in found}
            again: list[Item] = []
            for r in last.items:
                seen = taken_by(r, facts.effects)
                base = fresh.get(r.key) or Item(r.kind, r.key, r.evidence, effect=r.effect)
                state = "taken" if seen else "open" if r.key in fresh else "no longer suggested"
                again.append(_stamped(replace(base, n=r.n, state=state), brief_id))
            return tuple(again), ()
        return tuple(_stamped(i, brief_id) for i in picked.items), picked.held_back

    def _sections(
        self, facts: Facts, th: RetroThresholds, window: datetime | None, recs: tuple[BriefRecord, ...], last: BriefRecord | None, record: bool,
        held: tuple[Item, ...], d6_lines: tuple[str, ...], picked: Selection,
    ) -> tuple[Section, ...]:
        evaluated = [evaluate(t, th.window) for t in facts.tracked]
        carry_since = recs[-th.carry].since if th.carry and len(recs) >= th.carry else (self._clock.now() if th.carry == 0 else None)
        previous: tuple[Fate, ...] = fates(last, facts.effects, recorded=record)
        changes = changes_of(replace(facts.changes, briefs=recs), window)
        bad = facts.unreadable
        return (
            d1_said(facts.said, facts.accepts, bad), d2_passed(facts.passed, bad), d3_unlinked(facts.said, bad), d4_alarms(facts.alarms, facts.passed, bad),
            d5_repeated(groups(facts.one_offs, th.shape_overlap), bad, th), d6_health(facts.flags, d6_lines), d7_held(listed(evaluated, window, carry_since), bad),
            d8_changes(changes, window), d9_criteria(facts.sourced, facts.unknown_sources, bad), d10_proposals(facts.proposals, window, facts.oldest_event),
            d11_playbooks(facts.playbooks, bad), d12_spend(facts.spend, bad), d13_last(previous, last.id if last else None), d14_held(held),
        )
