"""The text and the JSON of the brief (design 4.7): the block the assistant shows to the user exactly as written, Details and the items for the assistant, and the form a program reads."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hirearchy.retro import Brief, Item, Section, brief_json, render_brief
from hirearchy.retro._changes import ChangeFacts
from hirearchy.retro._facts import Facts
from hirearchy.retro._ports import CharterVersions
from hirearchy.retro._views import OneOffCase
from hirearchy.retro.testing import briefs_over_fixed_facts

STARTED = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def one(case_id: str, title: str, day: int = 3) -> OneOffCase:
    return OneOffCase(case_id, "lead", title, ("Every action has an owner",), "Turn the notes into a list.", STARTED + timedelta(days=day), True, 4)


FACTS = Facts(
    one_offs=(one("M1", "Action list for 2026-10-05", 3), one("M2", "Action list for 2026-10-12", 10), one("M3", "Action list for 2026-10-19", 17)), estimates={"lead": 10},
    changes=ChangeFacts(versions=CharterVersions(True)), verdicts=3, cases=3,
)


def brief_of(tmp_path: Path, facts: Facts = FACTS, new: int = 1) -> Brief:
    return briefs_over_fixed_facts(tmp_path, facts, new=new, started=STARTED).briefs.brief()


def test_the_block_and_details_are_4_7s_texts(tmp_path: Path) -> None:
    text = render_brief(brief_of(tmp_path))
    block, _, rest = text.partition("RETRO BRIEF END\n")
    assert block == (
        "RETRO BRIEF B1 (since the organization started, 2026-10-01: 3 verdicts of yours on 3 cases)\n"
        "What you said:\n- none\nWhat got past a check:\n- none\nDid past changes hold:\n- none\nChanges to your organization:\n- none\n- Unprompted charter edits: 0\n"
        "Questions (one short answer each; any you leave lapse with no change at the next brief):\n"
        '1. Make the repeated task "action list for" a standing service of lead? You asked for it 3 times (2026-10-04, 2026-10-11, 2026-10-18). '
        "It costs nothing to set up; each request uses up to 10 runs, and is sent only when you ask.\n"
    )
    assert rest.startswith("Details (for you; the user need not read them):\nD1 What you said:\n- none\nD2 What got past a check:\n")
    assert "D10 Your team's own proposals:\n- Refusals since 2026-10-01: 0\n" in rest and "D13 The last brief:\n- no earlier brief\n" in rest
    assert (
        "Items:\n1. service (rung 2 of 7, adjust the standard: a one-off task has no contract to clarify (rung 1); a standing service gives these tasks one contract and lets "
        "the client's verdicts improve it)\n   Evidence: M1, M2, M3\n   Cost: up to 10 runs per request\n"
        "   Objection test (refuse it if it spends beyond the plan or lowers a criterion): spends within the plan: no run until you ask; lowers no criterion: the service's checks are the ones your tasks had\n"
        '   On yes: propose_org(blueprint=<the blueprint of this item>, extend="current")\n   {\n'
    ) in rest
    assert '"reason": "B1.1: 3 one-off tasks of one shape"' in rest and "   Revert: propose_org(blueprint=<the revert blueprint of this item>" in rest
    assert rest.endswith('Never add an item of your own.') and 'Next: show the block from "RETRO BRIEF" to "RETRO BRIEF END" to the user exactly as written.' in rest


def test_the_shown_again_heading_and_questions_line(tmp_path: Path) -> None:
    w = briefs_over_fixed_facts(tmp_path, FACTS, new=1, started=STARTED)
    w.briefs.brief()
    w.sources.new = 0
    text = render_brief(w.briefs.brief())
    assert text.startswith("RETRO BRIEF B1 (shown again: no verdict of yours since 2026-10-18, so nothing new is recorded)\n")
    assert "Questions (from B1; still open unless marked taken):\n1. Make the repeated task" in text


def test_the_questions_heading_asks_one_short_answer_each(tmp_path: Path) -> None:
    assert "Questions (one short answer each; any you leave lapse with no change at the next brief):" in render_brief(brief_of(tmp_path))


def test_a_taken_item_is_marked_taken(tmp_path: Path) -> None:
    brief = brief_of(tmp_path)
    taken = Brief(brief.id, brief.at, brief.since, brief.since_words, items=(Item("retire", "retire|a", ("a",), question="Retire a?", n=1, state="taken"),), shown_again="2026-10-18")
    assert "1. Retire a? (taken)" in render_brief(taken)


def test_empty_and_unreadable_sections(tmp_path: Path) -> None:
    brief = brief_of(tmp_path)
    broken = Section("d3", "Rejections with no criterion yet", (), ("- x",), (), "the record is damaged")
    text = render_brief(Brief(brief.id, brief.at, brief.since, brief.since_words, sections=(broken, Section("d1", "What you said", ("- none",), ("- none",)))))
    assert "D3 Rejections with no criterion yet:\n- cannot be read (the record is damaged)\n" in text and "D1 What you said:\n- none\n" in text


def test_no_item_reads_questions_none_this_time(tmp_path: Path) -> None:
    text = render_brief(brief_of(tmp_path, Facts(changes=ChangeFacts(versions=CharterVersions(True))), new=0))
    assert "Unprompted charter edits: 0\nQuestions: none this time.\nRETRO BRIEF END\n" in text and "\nItems: none (held back: 0).\n" in text
    held = Brief("B1", brief_of(tmp_path).at, None, "since the organization started", held_back=(Item("retire", "retire|a", ("a",)), Item("retire", "retire|b", ("b",))))
    assert "Items: none (held back: 2)." in render_brief(held)


def test_the_ledger_lines_are_in_the_block_and_the_threshold_notes_in_details(tmp_path: Path) -> None:
    brief = brief_of(tmp_path)
    noted = Brief(brief.id, brief.at, brief.since, brief.since_words, notes=("This brief was not recorded (disk full): the next one repeats it.", "retro.items in ORG.md is above 3: 3 is used (a brief has at most 3 items)."))
    text = render_brief(noted)
    block, _, rest = text.partition("RETRO BRIEF END")
    assert "This brief was not recorded (disk full): the next one repeats it." in block and "retro.items in ORG.md is above 3" not in block and "retro.items in ORG.md is above 3" in rest


def test_every_question_is_one_sentence_under_300_characters_ending_with_a_question_mark(tmp_path: Path) -> None:
    long = "x" * 400
    cases = tuple(OneOffCase(f"M{n}", "lead", f"Action list for {long[:50]} 2026-10-{n:02d}", ("Every action has an owner",), "g", STARTED + timedelta(days=n), True, 4) for n in (1, 2, 3))
    items = brief_of(tmp_path, Facts(one_offs=cases, estimates={"lead": 10}, changes=ChangeFacts(versions=CharterVersions(True)))).items
    from hirearchy.retro._signals import answer_items, cause_items, clarify_items, idle_items
    from hirearchy.retro._views import HealthFlag, Passed, Said, Sourced
    from hirearchy.retro import RetroThresholds

    more = [
        *items, *cause_items([Passed("memos", "M1", "T1", "lead/c", True, ("R3",), ("C4",), "untyped", (), None, long)]),
        *clarify_items([Sourced("memos", "C1", long, "user", long, long, "", ("a", "b", "c"), 5, 5)], RetroThresholds()), *idle_items([HealthFlag("ceo/x", "idle", "r", 2, "2d")], {}, {})[0],
        *answer_items([Said("memos", "R6", "M1", None, "Too long.", question='About C3: add "<the rule, in their words>" as a lasting rule? Yes or no.')]),
    ]
    assert len(more) == 5
    for item in more:
        assert len(item.question) < 300 and "?" in item.question, item.question  # the design's own texts: a question, with the facts after it where it has any


def test_brief_json_has_every_section_and_every_count_with_its_n(tmp_path: Path) -> None:
    data = brief_json(brief_of(tmp_path))
    assert json.loads(json.dumps(data)) == data  # it is JSON
    sections = data["sections"]
    assert isinstance(sections, dict) and list(sections) == [f"d{n}" for n in range(1, 15)]
    assert sections["d1"]["counts"] == {"rejections": 0, "accepts": 0} and sections["d8"]["counts"] == {"changes": 0, "unprompted_charter_edits": 0}
    assert sections["d10"]["counts"] == {"proposals_refused": 0, "refusals": 0} and sections["d13"]["counts"] == {"items": 0, "taken": 0, "lapsed": 0}
    assert (data["id"], data["verdicts"], data["cases"], data["recorded"], data["since"]) == ("B1", 3, 3, True, STARTED.isoformat())
    items = data["items"]
    assert isinstance(items, list) and len(items) == 1
    item = items[0]
    assert item["key"] == "service|lead|M1" and item["n"] == 1 and item["evidence"] == ["M1", "M2", "M3"] and json.loads(item["blueprint"])["extend"]["add_services"]
