"""``RuleWatchSettler`` (design 8.5): two related rejections retire the watched text and restore the text before the watch, one version per item in
id order, each write a compare-and-swap; the notes of 8.3; a failed write is recorded, never raised (unless the caller asks for it). The watch is the
stand-in's (``AdmittingServiceEvidence(watch=...)``): ``reflection`` derives the real one and has its own tests."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from hirearchy.kernel import OrgError, split_frontmatter
from hirearchy.services import AmendmentBasis, ItemWatch, PlaybookRace, Rejection
from hirearchy.services._items import parse_items
from hirearchy.services._texts import EventedPlaybookWriter
from hirearchy.services._watch import RuleWatchSettler, SettleReport
from hirearchy.services.testing import AdmittingServiceEvidence, ServicesWorld, fs_world

from ._support import define, populated

SERVICE = "weekly-brief"
PLAYBOOK = f"ceo/services/{SERVICE}/PLAYBOOK.md"
JAN2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
V1 = (
    "## Steps\n1. [P1] Search.\n2. [P2] Write the memo.\n\n"
    "## Rules\n- [P3] WHEN always THEN Cite every claim. WHY R1; C2"
)
V2 = (
    "## Steps\n1. [P1] Search.\n2. [P2] Write the memo.\n\n"
    "## Rules\n- [P3] WHEN a claim is new THEN Cite it twice. WHY R2, R3; C4"
)
V1_RESTORED = V1  # the text before the watch comes back in place, with its own WHY


def written(w: ServicesWorld, version: int, body: str, items_max: int, why: dict[str, list[str]], rules: tuple[str, ...] = ("P3",), **meta: Any) -> None:
    """The files hold an item-form version (a change admitted earlier, whatever the gate says now), revised on January ``version``."""
    given = {
        "service": SERVICE, "version": version, "revised": f"2026-01-0{version}T00:00:00+00:00", "by": "ceo", "reason": "earlier", "items_max": items_max,
        "rules": list(rules), "why": why, "op": "edit", "admitted": "b", **meta,
    }
    w.store.write_playbook("ceo", SERVICE, version, given, body, version - 1 or None)


def due(item: str = "P3", kind: str = "rule", version: int = 2, related: Sequence[str] = ("R4", "R6"), start: datetime | None = JAN2, **kw: Any) -> ItemWatch:
    return ItemWatch(item, kind, "warning", version, start, related=tuple(related), retire_due=len(related) >= 2, **kw)


def seeded(tmp_path: Path, *watch: ItemWatch, locked: bool = False, basis: AmendmentBasis | None = None) -> ServicesWorld:
    """v1 (P3 reads "Cite every claim.") and v2 (P3 edited, the watched change) are written; the stand-in says ``watch``."""
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(basis=basis, watch=watch)))
    define(w, locked=locked)
    written(w, 1, V1, 3, {"P3": ["R1", "C2"]}, op="first")
    written(w, 2, V2, 3, {"P3": ["R2", "R3", "C4"]}, item="P3")
    return w


def settler(w: ServicesWorld, writer: Any = None) -> RuleWatchSettler:
    from hirearchy.dispatch.testing import PostedDelivery

    return RuleWatchSettler(w.catalog, w.evidence, writer or EventedPlaybookWriter(w.store, w.d.clock, w.events), PostedDelivery(w.d.post))


def meta_of(w: ServicesWorld) -> tuple[dict[str, Any], str]:
    text = w.text(PLAYBOOK)
    assert text is not None
    meta, body = split_frontmatter(text)
    return dict(meta), body.strip()


def versions(w: ServicesWorld) -> int:
    return w.catalog.read_playbook("ceo", SERVICE).version


def rejected(case: str = "t0") -> AmendmentBasis:
    return AmendmentBasis((Rejection("m4", "R4", "t4", "T", (), "no", "", case=case),), ())


# ============================================================================================== the retire and the restore (8.5)


def test_two_related_rejections_retire_the_watched_text_and_restore_the_text_before_the_watch(tmp_path: Path) -> None:
    w = seeded(tmp_path, due())
    report = settler(w).settle("ceo", SERVICE, (due(),))
    assert report == SettleReport(retired=("P3",), warned=(), failed=())
    playbook = w.catalog.read_playbook("ceo", SERVICE)
    assert playbook.version == 3 and playbook.body == V1_RESTORED  # P3 is the text of v1 again, in its place, with its WHY
    assert [(i.id, i.text, i.when, i.why) for i in playbook.items or () if i.id == "P3"] == [("P3", "Cite every claim.", "always", ("R1", "C2"))]


def test_the_watch_versions_frontmatter(tmp_path: Path) -> None:
    w = seeded(tmp_path, due())
    settler(w).settle("ceo", SERVICE, (due(),))
    meta, body = meta_of(w)
    assert meta["version"] == 3
    assert (meta["op"], meta["admitted"], meta["by"], meta["item"], meta["related"], meta["restores"]) == ("watch", "watch", "runtime (watch)", "P3", ["R4", "R6"], 1)
    assert meta["reason"] == "the client rejected R4 and R6, which are about R2, R3, C4"
    assert meta["why"] == {"P3": ["R1", "C2"]} and meta["rules"] == ["P3"] and meta["items_max"] == 3
    assert body == V1_RESTORED
    assert w.text(f"ceo/services/{SERVICE}/history/PLAYBOOK.v2.md") is not None  # the version it replaced is kept
    (event,) = [e for e in w.events.events if e.kind == "service.revise"]
    assert (event.actor, event.fields["by"], event.fields["admitted"], event.fields["version"]) == ("runtime", "runtime (watch)", "watch", 3)


def test_a_retire_without_a_previous_text_removes_the_item(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=(due("P2", "step", 2),))))
    define(w)
    written(w, 1, "## Steps\n1. [P1] Search.", 1, {}, rules=(), op="first")
    written(w, 2, "## Steps\n1. [P1] Search.\n2. [P2] Write the memo. (WHY R2, R3)", 2, {"P2": ["R2", "R3"]}, rules=(), item="P2")
    report = settler(w).settle("ceo", SERVICE, ())
    assert report.retired == ("P2",)
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search." and meta["items_max"] == 2 and meta["op"] == "watch" and "restores" not in meta  # the id is never reused
    assert meta["related"] == ["R4", "R6"]


def test_a_previous_text_with_the_watched_texts_tokens_restores_nothing(tmp_path: Path) -> None:
    """R3-F8: a restore of the client-written text restarted the watch on exactly the text before it: putting it back would write an unchanged body."""
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=(due(version=3),))))
    define(w)
    written(w, 1, V1, 3, {"P3": ["R1", "C2"]}, op="first")
    written(w, 2, V2, 3, {"P3": ["R2", "R3", "C4"]}, item="P3")
    written(w, 3, "## Steps\n1. [P1] Search.\n2. [P2] Write the memo.\n\n## Rules\n- [P3] WHEN always THEN Cite every claim.", 3, {}, item="P3", op="restore", admitted="restore")
    report = settler(w).settle("ceo", SERVICE, ())
    assert report.retired == ("P3",)
    meta, body = meta_of(w)
    assert body == "## Steps\n1. [P1] Search.\n2. [P2] Write the memo." and meta["op"] == "watch" and "restores" not in meta and meta["rules"] == []


def test_one_version_per_item_in_id_order(tmp_path: Path) -> None:
    both = (due("P3", "rule"), due("P2", "step"))
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=both)))
    define(w)
    written(w, 1, V1, 3, {"P3": ["R1", "C2"]}, op="first")
    written(w, 2, V2.replace("2. [P2] Write the memo.", "2. [P2] Write the memo twice. (WHY R2, R3; C4)"), 3, {"P2": ["R2", "R3", "C4"], "P3": ["R2", "R3", "C4"]}, item="P2")
    report = settler(w).settle("ceo", SERVICE, ())
    assert report.retired == ("P2", "P3")
    assert versions(w) == 4
    assert [(p.version, p.op, p.item) for p in w.catalog.playbook_versions("ceo", SERVICE)][-2:] == [(3, "watch", "P2"), (4, "watch", "P3")]
    assert w.catalog.read_playbook("ceo", SERVICE).body == V1  # both texts before the watch are back, in their places


def test_an_item_whose_text_lost_the_watched_tokens_is_left_to_the_next_derivation(tmp_path: Path) -> None:
    """A gated change the owner wrote meanwhile restarted the watch (W2): the stale derivation retires nothing of it."""
    w = seeded(tmp_path, due())
    written(w, 3, V2.replace("Cite it twice.", "Cite it three times."), 3, {"P3": ["R2", "R3", "C4"]}, item="P3")
    report = settler(w).settle("ceo", SERVICE, ())
    assert report == SettleReport() and versions(w) == 3


def test_a_second_settler_that_finds_the_item_gone_writes_nothing(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(watch=(due("P2", "step", 2),))))
    define(w)
    written(w, 1, "## Steps\n1. [P1] Search.", 1, {}, rules=(), op="first")
    written(w, 2, "## Steps\n1. [P1] Search.\n2. [P2] Write the memo. (WHY R2, R3)", 2, {"P2": ["R2", "R3"]}, rules=(), item="P2")
    assert settler(w).settle("ceo", SERVICE, ()).retired == ("P2",)
    assert settler(w).settle("ceo", SERVICE, ()) == SettleReport()  # the stand-in still says "due", the file says gone
    assert versions(w) == 3


# ============================================================================================== the notes (8.3)


def test_the_warning_note_at_0_to_1(tmp_path: Path) -> None:
    one = due(related=("R4",))
    w = seeded(tmp_path, one, basis=rejected("t0"))
    report = settler(w).settle("ceo", SERVICE, (due(related=()),))
    assert report == SettleReport(warned=("P3",)) and versions(w) == 2
    (note,) = [m for m in w.d.inbox("ceo") if m.sender == "runtime"]
    assert note.title == "playbook item P3 of weekly-brief: warning"
    assert note.body == (
        "Rejection R4 (case t0) is about R2, R3, C4, which P3 cites. One more related rejection retires P3 and restores the text of v1. "
        "Follow the contract where they differ."
    )
    assert note.wake is False and [m for m in w.d.inbox("root") if m.sender == "runtime"] == []  # to the owner only
    assert settler(w).settle("ceo", SERVICE, (one,)) == SettleReport()  # nothing changed: nothing is sent again
    assert len([m for m in w.d.inbox("ceo") if m.sender == "runtime"]) == 1


def test_a_warning_without_a_previous_text_does_not_promise_a_restore(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path, AdmittingServiceEvidence(basis=rejected(), watch=(due("P2", "step", 2, related=("R4",)),))))
    define(w)
    written(w, 1, "## Steps\n1. [P1] Search.", 1, {}, rules=(), op="first")
    written(w, 2, "## Steps\n1. [P1] Search.\n2. [P2] Write the memo. (WHY R2, R3)", 2, {"P2": ["R2", "R3"]}, rules=(), item="P2")
    settler(w).settle("ceo", SERVICE, None)
    assert not w.d.inbox("ceo")  # before unknown: no warning note either
    settler(w).settle("ceo", SERVICE, (due("P2", "step", 2, related=()),))
    (note,) = w.d.inbox("ceo")
    assert note.body == (
        "Rejection R4 (case t0) is about R2, R3, which P2 cites. One more related rejection retires P2. Follow the contract where they differ."
    )


def test_the_retire_note_to_owner_and_parent_names_ids_only_for_root(tmp_path: Path) -> None:
    w = seeded(tmp_path, due())
    settler(w).settle("ceo", SERVICE, (due(),))
    expected = (
        "Rejections R4 and R6 are about R2, R3, C4, which P3 cited, so the runtime retired it and restored the text of v1 (playbook v3). "
        "The client's verdicts decide this; no acknowledgement is needed."
    )
    for to in ("ceo", "root"):
        (note,) = [m for m in w.d.inbox(to) if m.sender == "runtime"]
        assert note.title == "playbook of weekly-brief: the watch retired P3" and note.body == expected and note.wake is False
        assert "Cite it twice" not in note.body and "Cite every claim" not in note.body  # ids only, never the item's words


def test_0_to_2_in_one_call_sends_the_retire_note_and_no_warning(tmp_path: Path) -> None:
    w = seeded(tmp_path, due(), basis=rejected())
    report = settler(w).settle("ceo", SERVICE, (due(related=()),))
    assert report == SettleReport(retired=("P3",))
    assert [m.title for m in w.d.inbox("ceo") if m.sender == "runtime"] == ["playbook of weekly-brief: the watch retired P3"]


# ============================================================================================== failure and concurrency (8.5)


class Failing:
    """A playbook writer whose write fails with ``error``."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def write(self, *args: Any, **kw: Any) -> str:
        raise self._error


def test_a_failed_write_is_recorded_as_failed_never_raised(tmp_path: Path) -> None:
    w = seeded(tmp_path, due())
    report = settler(w, Failing(OSError("disk full"))).settle("ceo", SERVICE, ())
    assert report == SettleReport(failed=(("P3", "disk full"),)) and versions(w) == 2
    assert not [m for m in w.d.inbox("root") if m.sender == "runtime"]  # nothing was retired, so nothing is announced
    with pytest.raises(OSError, match="disk full"):  # the owner's op meets the same failure as any write failure (strict)
        settler(w, Failing(OSError("disk full"))).settle("ceo", SERVICE, (), strict=True)


def test_playbook_race_is_recorded_as_failed(tmp_path: Path) -> None:
    w = seeded(tmp_path, due())
    report = settler(w, Failing(PlaybookRace(3))).settle("ceo", SERVICE, ())
    assert [item for item, _ in report.failed] == ["P3"] and "v3" in report.failed[0][1] and report.retired == ()
    with pytest.raises(PlaybookRace):  # strict: the owner's op turns it into PB-RACE
        settler(w, Failing(PlaybookRace(3))).settle("ceo", SERVICE, (), strict=True)


def test_an_unreadable_watch_is_recorded_not_raised(tmp_path: Path) -> None:
    class Unreadable(AdmittingServiceEvidence):
        def watch(self, owner: str, service: str) -> tuple[ItemWatch, ...]:
            raise OrgError("the mail cannot be read")

    w = seeded(tmp_path)
    w2 = RuleWatchSettler(w.catalog, Unreadable(), EventedPlaybookWriter(w.store, w.d.clock, w.events), w_delivery(w))
    assert w2.settle("ceo", SERVICE, ()) == SettleReport(failed=(("", "the mail cannot be read"),))
    assert w2.settle("ceo", SERVICE, (), strict=True) == SettleReport(failed=(("", "the mail cannot be read"),))  # a read that fails writes nothing either way


def w_delivery(w: ServicesWorld) -> Any:
    from hirearchy.dispatch.testing import PostedDelivery

    return PostedDelivery(w.d.post)


def test_a_locked_contract_still_retires(tmp_path: Path) -> None:
    """The lock stops the owner's ops, not the client's verdicts (8.5)."""
    w = seeded(tmp_path, due(), locked=True)
    assert settler(w).settle("ceo", SERVICE, ()).retired == ("P3",)
    assert versions(w) == 3


class Rebuilt(AdmittingServiceEvidence):
    """The watch the files derive: ``broken`` while the playbook is at v2 (hand-edited), ``repaired`` once it has been repaired."""

    def __init__(self, catalog: Any, broken: Sequence[ItemWatch], repaired: Sequence[ItemWatch]) -> None:
        super().__init__()
        self._catalog = catalog
        self._broken = tuple(broken)
        self._repaired = tuple(repaired)

    def watch(self, owner: str, service: str) -> tuple[ItemWatch, ...]:
        return self._broken if self._catalog.read_playbook(owner, service).version == 2 else self._repaired


def test_an_unparseable_body_is_repaired_first_then_retired(tmp_path: Path) -> None:
    w = populated(fs_world(tmp_path))
    define(w)
    written(w, 1, "## Steps\n1. [P1] Search.", 1, {}, rules=(), op="first")
    written(w, 2, "## Steps\n1. [P1] Search.\nan extra line a hand added\n\n## Rules\n- [P2] WHEN always THEN Cite it twice.", 2, {}, rules=("P2",), item="P2")
    assert w.catalog.read_playbook("ceo", SERVICE).parse_error  # the body does not parse
    evidence = Rebuilt(w.catalog, [due("P2", "rule", 2)], [due("P4", "step", 2)])  # the repair gives the migrated lines new ids; the watch is carried to one
    report = RuleWatchSettler(w.catalog, evidence, EventedPlaybookWriter(w.store, w.d.clock, w.events), w_delivery(w)).settle("ceo", SERVICE, ())
    assert report.retired == ("P4",) and report.failed == ()
    kinds = [(p.version, p.op, p.by) for p in w.catalog.playbook_versions("ceo", SERVICE)]
    assert kinds[-2:] == [(3, "migrate", "runtime (migration)"), (4, "watch", "runtime (watch)")]
    final = w.catalog.read_playbook("ceo", SERVICE)
    assert final.parse_error == "" and "P4" not in {i.id for i in final.items or ()}


def test_the_round_trip_is_asserted_before_the_write(tmp_path: Path) -> None:
    """The body handed to the writer parses back, with the frontmatter handed with it, to the items it was rendered from."""
    w = seeded(tmp_path, due())
    seen: list[tuple[str, dict[str, Any]]] = []

    class Spy:
        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def write(self, owner: str, name: str, version: int, body: str, by: str, reason: str, archive: int | None = None, extra: Any = None) -> str:
            seen.append((body, dict(extra)))
            return str(self._inner.write(owner, name, version, body, by, reason, archive, extra))

    settler(w, Spy(EventedPlaybookWriter(w.store, w.d.clock, w.events))).settle("ceo", SERVICE, ())
    (body, extra), = seen
    parsed = parse_items(body, extra)
    assert parsed.error == "" and [i.id for i in parsed.items] == ["P1", "P2", "P3"] and parsed.items[2].text == "Cite every claim."
    assert split_frontmatter(w.text(PLAYBOOK) or "")[1].strip() == body.strip()


# ============================================================================================== the restore a retire would make, for the owner's states line (14.1)
def test_watch_restores_names_the_version_a_retire_would_bring_back(tmp_path: Path) -> None:
    from hirearchy.services import watch_restores

    w = seeded(tmp_path)
    watch = ItemWatch("P3", "rule", "warning", 2, JAN2, related=("R4",))
    assert watch_restores(w.catalog.playbook_versions("ceo", SERVICE), watch) == 1  # the text before the watch is v1's


def test_watch_restores_is_zero_for_an_item_with_no_earlier_text(tmp_path: Path) -> None:
    from hirearchy.services import watch_restores

    w = seeded(tmp_path)
    versions_ = w.catalog.playbook_versions("ceo", SERVICE)
    assert watch_restores(versions_, ItemWatch("P3", "rule", "warning", 1, datetime(2026, 1, 1, tzinfo=timezone.utc), related=("R4",))) == 0  # watch starts at v1
    assert watch_restores(versions_, ItemWatch("P9", "step", "warning", 2, JAN2, related=("R4",))) == 0  # an id no version holds
    assert watch_restores(versions_, ItemWatch("P3", "rule", "warning", 2, None, related=("R4",))) == 0  # never watched
