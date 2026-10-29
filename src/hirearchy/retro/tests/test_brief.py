"""The brief, recorded or shown again (design 4.2, 4.8): it is recorded as the next B when a verdict of the user arrived since the last one, and shown again, recorded nowhere,
otherwise; a ledger that cannot be read counts every verdict as new; one that cannot be written still returns the brief, with its line. Over fixed facts and a ledger in memory."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import hirearchy.retro
from hirearchy.kernel import OrgError
from hirearchy.retro._changes import ChangeFacts
from hirearchy.retro._facts import Facts
from hirearchy.retro._ports import CharterVersions
from hirearchy.retro._views import OneOffCase
from hirearchy.retro.testing import BriefsWorld, briefs_over_fixed_facts

STARTED = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
GIT = ChangeFacts(versions=CharterVersions(True))


def one(case_id: str, title: str) -> OneOffCase:
    return OneOffCase(case_id, "lead", title, ("Every action has an owner",), "Turn the notes into a list.", STARTED + timedelta(days=2), True, 4)


REPEATED = Facts(one_offs=(one("M1", "Action list for 2026-10-05"), one("M2", "Action list for 2026-10-12"), one("M3", "Action list for 2026-10-19")), estimates={"lead": 10}, changes=GIT, verdicts=3, cases=3)


def world(tmp_path: Path, facts: Facts | None = None, new: int = 1, started: datetime | None = STARTED) -> BriefsWorld:
    return briefs_over_fixed_facts(tmp_path, facts, new=new, started=started)


def test_an_organization_with_nothing_gives_every_section_none_and_no_item(tmp_path: Path) -> None:
    brief = world(tmp_path, Facts(changes=GIT), new=0).briefs.brief()
    assert brief.items == () and brief.held_back == () and brief.notes == ()
    assert [s.key for s in brief.sections] == [f"d{n}" for n in range(1, 15)]
    assert {s.key for s in brief.sections if "- none" in s.details} == {"d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "d11", "d14"}  # d10 counts refusals, d12 states its basis, d13 says there is no earlier brief
    assert brief.sections[12].details == ("- no earlier brief",) and (brief.verdicts, brief.cases) == (0, 0)


def test_no_earlier_brief_counts_from_the_organizations_start_and_records_b1(tmp_path: Path) -> None:
    w = world(tmp_path, new=0)
    brief = w.briefs.brief()
    assert (brief.id, brief.recorded, brief.since, brief.since_words) == ("B1", True, STARTED, "since the organization started, 2026-10-01")
    assert [r.id for r in w.records.records()] == ["B1"] and w.records.last() is not None and w.records.last().since == STARTED  # type: ignore[union-attr]
    assert w.sources.reads == [(STARTED, None)]
    undated = world(tmp_path, new=0, started=None).briefs.brief()
    assert (undated.since, undated.since_words) == (None, "since the organization started")


def test_a_second_call_with_no_verdict_shows_the_last_brief_again_and_writes_nothing(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED)
    first = w.briefs.brief()
    assert [i.key for i in first.items] == ["service|lead|M1"] and first.recorded
    w.sources.new = 0
    again = w.briefs.brief()
    assert (again.id, again.recorded, again.shown_again != "") == ("B1", False, True)
    assert [(i.n, i.key, i.state) for i in again.items] == [(1, "service|lead|M1", "open")] and again.items[0].question == first.items[0].question
    assert len(w.records.records()) == 1 and w.sink.events == []
    assert w.sources.reads[-1][0] == STARTED  # the readings are derived afresh over the window of the brief shown


def test_one_new_verdict_records_the_next_brief_and_lapses_the_untaken_items(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED)
    w.briefs.brief()
    w.clock.advance(3600)
    second = w.briefs.brief()
    assert (second.id, second.recorded, second.since_words.startswith("since the last brief, ")) == ("B2", True, True)
    assert second.items == () and [r.id for r in w.records.records()] == ["B1", "B2"]  # the item was not taken: it lapsed, and the same evidence does not bring it back
    assert second.sections[12].details == ("- B1.1 service: lapsed: no change",)
    assert w.records.asked() == frozenset({"service|lead|M1"})


def test_a_look_back_is_recorded_nowhere_and_its_items_would_be(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED)
    back = w.briefs.brief(since=STARTED + timedelta(days=1))
    assert (back.id, back.recorded, back.since_words) == ("look-back", False, "since 2026-10-02 (a look-back; not recorded)")
    assert [i.key for i in back.items] == ["service|lead|M1"] and w.records.records() == ()
    assert "B1.1" not in back.items[0].blueprint and "look-back.1" in back.items[0].blueprint  # a look-back item is named for what it is


def test_a_shown_again_brief_re_renders_details_or_says_no_longer_suggested(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED)
    w.briefs.brief()
    w.sources.new = 0
    w.sources.facts = Facts(changes=GIT)  # the evidence is gone
    gone = w.briefs.brief().items[0]
    assert (gone.n, gone.kind, gone.key, gone.state) == (1, "service", "service|lead|M1", "no longer suggested")


def test_an_unreadable_ledger_counts_every_verdict_as_new_and_lapses_nothing(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED, new=0)
    w.records.unreadable = "briefs is not a list"
    brief = w.briefs.brief()
    assert brief.notes[0] == "The record of earlier briefs cannot be read (.runtime/retros.json is not a record of briefs (briefs is not a list)): this brief counts every verdict as new and lapses nothing."
    assert brief.id == "B1" and brief.recorded and [r.id for r in w.records.records()] == ["B1"]  # the append replaced the ledger
    assert [e.kind for e in w.sink.events] == ["retro.ledger_unreadable"] and "briefs is not a list" in str(w.sink.events[0].fields["error"])


def test_an_unwritable_ledger_returns_the_brief_with_its_line(tmp_path: Path) -> None:
    w = world(tmp_path, REPEATED)
    w.records.unwritable = "No space left on device"
    brief = w.briefs.brief()
    assert brief.recorded is False and [i.key for i in brief.items] == ["service|lead|M1"]
    assert brief.notes == ("This brief was not recorded (.runtime/retros.json cannot be written: No space left on device): the next one repeats it.",)
    assert [e.kind for e in w.sink.events] == ["retro.record_failed"] and w.records.records() == ()


def test_a_future_since_is_refused(tmp_path: Path) -> None:
    w = world(tmp_path)
    with pytest.raises(OrgError, match=r"^refused: since is in the future \(2026-10-\d\d\)\. Nothing was read\.$"):
        w.briefs.brief(since=w.clock.now() + timedelta(days=2))
    assert w.sources.reads == [] and w.records.records() == ()


def test_without_git_the_charter_lines_read_unknown(tmp_path: Path) -> None:
    d8 = world(tmp_path, Facts()).briefs.brief().sections[7]
    assert d8.block == ("- charter history unknown (no git history)", "- Unprompted charter edits: unknown")
    assert d8.counts == (("changes", 0), ("unprompted_charter_edits", "unknown"))


def test_the_thresholds_notes_are_in_the_brief(tmp_path: Path) -> None:
    w = briefs_over_fixed_facts(tmp_path, Facts(changes=GIT), org_md="---\nmission: m\nretro:\n  items: 9\n---\nrules\n")
    assert w.briefs.brief().notes == ("retro.items in ORG.md is above 3: 3 is used (a brief has at most 3 items).",)


def test_retro_sends_no_message() -> None:
    package = Path(hirearchy.retro.__file__).resolve().parent
    imported, called = set(), set()
    for path in package.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 2 and node.module:
                imported.add(node.module.split(".")[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    assert not imported & {"dispatch", "delivery", "hierarchy"} and not called & {"send", "notify", "deliver", "delegate"}
