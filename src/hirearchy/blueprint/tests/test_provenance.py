"""Criteria provenance (design 10.1, F-P1-3): a criterion may declare where it comes from, and a plan records the user's words."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint._firsttask import FirstTaskGiver
from hirearchy.blueprint._provenance import criterion_issues
from hirearchy.blueprint._view import NEEDS_KEYS, criteria_of, svc_criteria
from hirearchy.blueprint.api import Agent, Issue
from hirearchy.blueprint.testing import CallLog, RecordingServiceCommands, RecordingTaskAssigner
from testkit.blueprint_world import bpm

WORDS = "Use the words from the notes. Owners: initials."
QUOTE = "Use the words from the notes."


def plain(*criteria: object, elicitation: object = WORDS) -> dict[str, object]:
    needs: dict[str, object] = {} if elicitation is None else {"elicitation": elicitation}
    return {"mission": "m", "needs": needs, "task": {"title": "t", "goal": "g", "acceptance": list(criteria)}}


def serviced(*criteria: object, elicitation: object = WORDS) -> dict[str, object]:
    needs: dict[str, object] = {} if elicitation is None else {"elicitation": elicitation}
    return {"mission": "m", "needs": needs, "services": [{"name": "brief", "acceptance": list(criteria)}]}


def found(bp: dict[str, object], *, extension: bool = False, require_sources: bool = False) -> list[Issue]:
    return criterion_issues(bp, extension=extension, require_sources=require_sources)


def codes(issues: list[Issue]) -> list[tuple[str, str]]:
    return [(i.level, i.code) for i in issues]


# ------------------------------------------------------------------------------------------------ a mapping criterion is its text


def test_a_mapping_criterion_is_its_text_everywhere_downstream() -> None:
    bp = plain({"text": "Every row has a date.", "from": QUOTE}, "At most 3 sections.", {"text": "Cite 2 sources.", "default": True})
    assert criteria_of(bp) == ["Every row has a date.", "At most 3 sections.", "Cite 2 sources."]
    assert svc_criteria({"acceptance": [{"text": " A  ", "default": True}, "", {"text": "", "default": True}, "B"]}) == ["A", "B"]
    log = CallLog()
    FirstTaskGiver(RecordingTaskAssigner(log), RecordingServiceCommands(log)).give(
        bp, Agent(addr="lead", name="lead", parent=None, where="agents[lead]"), 9,
    )
    (call,) = log.of("delegate")
    assert call.args[4] == "1. Every row has a date.\n2. At most 3 sections.\n3. Cite 2 sources."


# ------------------------------------------------------------------------------------------------ criterion-from


def test_a_quote_not_in_the_recorded_words_is_criterion_from() -> None:
    issues = found(plain({"text": "Every row has a date.", "from": "Dates in every row"}))
    assert issues == [Issue(
        "error", "task.acceptance[1]",
        'criterion 1 quotes words that are not in needs.elicitation: "Dates in every row". Quote the user\'s own words exactly, or mark it '
        "default: true.", "criterion-from",
    )]
    only_second = found(serviced("plain one", {"text": "x y z w", "from": "nothing like it"}))
    assert [(i.path, i.code) for i in only_second] == [("services[brief].acceptance[2]", "criterion-from")]


def test_a_quote_without_needs_elicitation_is_criterion_from() -> None:
    issues = found(plain({"text": "Every row has a date.", "from": QUOTE}, elicitation=None))
    assert issues == [Issue(
        "error", "task.acceptance[1]",
        "criterion 1 quotes the user, but needs.elicitation is missing: put their answers there, verbatim.", "criterion-from",
    )]


def test_whitespace_and_case_are_folded_before_the_substring_test() -> None:
    bp = plain({"text": "x y z w", "from": "  use THE words\nfrom   the notes. "}, elicitation="Hi.  Use the words\tfrom the NOTES.  Owners: initials.")
    assert found(bp) == []


def test_a_mapping_without_text_or_with_two_sources_or_an_unknown_key_is_criterion_form() -> None:
    cases: list[object] = [
        {"from": QUOTE}, {"text": "  ", "default": True}, {"text": 5, "default": True},
        {"text": "a b c d", "from": QUOTE, "default": True}, {"text": "a b c d", "default": True, "from_tasks": ["x"]},
        {"text": "a b c d", "default": False}, {"text": "a b c d", "default": "yes"}, {"text": "a b c d", "from": ""}, {"text": "a b c d", "from": 7},
        {"text": "a b c d", "default": True, "color": "red"}, {"text": "x" * 1001, "default": True}, {"text": "a b c d", "from": QUOTE + "x" * 1000},
    ]
    for case in cases:
        issues = found(plain(case))
        assert [(i.level, i.path, i.code) for i in issues if i.code == "criterion-form"] == [("error", "task.acceptance[1]", "criterion-form")], case


def test_from_tasks_outside_an_extension_is_criterion_form() -> None:
    bp = serviced({"text": "a b c d", "from_tasks": ["t-1"]})
    (issue,) = found(bp)
    assert (issue.level, issue.path, issue.code) == ("error", "services[brief].acceptance[1]", "criterion-form")
    assert "extension" in issue.message
    assert found(bp, extension=True) == []
    assert codes(found(serviced({"text": "a b c d", "from_tasks": []}), extension=True)) == [("error", "criterion-form")]
    assert codes(found(serviced({"text": "a b c d", "from_tasks": ["t"] * 21}), extension=True)) == [("error", "criterion-form")]
    assert codes(found(serviced({"text": "a b c d", "from_tasks": "t-1"}), extension=True)) == [("error", "criterion-form")]


def test_needs_elicitation_is_a_known_needs_key_of_1_to_4000_characters() -> None:
    assert "elicitation" in NEEDS_KEYS
    assert found(plain("a plain criterion", elicitation="x" * 4000)) == []
    for bad in ("x" * 4001, 5, ["a"]):
        assert codes(found(plain("a plain criterion", elicitation=bad))) == [("error", "criterion-words")], bad
    assert found(plain("a plain criterion", elicitation="   ")) == []  # blank counts as missing (strict plans refuse it, commit 6)
    unknown_key = [i for i in bpm.validate({**plain("a plain criterion"), "needs": {"elicitation": "ok"}}) if i.code == "unknown-key"]
    assert not any("elicitation" in i.message for i in unknown_key)


def test_asked_is_at_most_300_characters_and_only_with_from() -> None:
    assert found(plain({"text": "a b c d", "from": QUOTE, "asked": "q" * 300})) == []
    assert codes(found(plain({"text": "a b c d", "from": QUOTE, "asked": "q" * 301}))) == [("error", "criterion-form")]
    assert codes(found(plain({"text": "a b c d", "from": QUOTE, "asked": 5}))) == [("error", "criterion-form")]
    assert codes(found(plain({"text": "a b c d", "default": True, "asked": "why?"}))) == [("error", "criterion-form")]


def test_the_validator_reports_the_provenance_issues_with_the_rest(tmp_path: Path) -> None:
    bp = plain({"text": "Every row has a date.", "from": "nothing like it"})
    assert "criterion-from" in {i.code for i in bpm.validate(bp, allowed_roots=[tmp_path])}


@pytest.mark.parametrize("bp", [{}, {"task": "text"}, {"task": {"acceptance": "one line"}}, {"services": "no"}, {"services": [3, {"acceptance": None}]}])
def test_a_blueprint_of_the_wrong_shape_has_no_provenance_issue(bp: dict[str, object]) -> None:
    assert found(bp) == []
