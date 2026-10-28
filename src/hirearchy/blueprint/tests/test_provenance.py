"""Criteria provenance (design 10.1, F-P1-3): a criterion may declare where it comes from, and a plan records the user's words."""

from __future__ import annotations

from pathlib import Path

import pytest
import testkit
import yaml

from hirearchy.blueprint._firsttask import FirstTaskGiver
from hirearchy.blueprint._provenance import NO_RECORD, criterion_issues
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
    """The issues of the form and quote rules (the two that a plan without sources earns are asked for by ``sourcing``)."""
    return [i for i in sourcing(bp, extension=extension, require_sources=require_sources) if i.code != "criterion-source" and i.message != NO_RECORD]


def sourcing(bp: dict[str, object], *, extension: bool = False, require_sources: bool = False) -> list[Issue]:
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


# ------------------------------------------------------------------------------------------------ the gate: one line under every criterion

EXAMPLE = testkit.REPO / "examples" / "blueprint-research.yaml"
ASKED = "Owners: initials or full names?"
P1_WORDS = "Owners: initials. Use the words from the notes."
P1_LINE = (
    'from your words "Use the words from the notes." (my question: "Owners: initials or full names?"); '
    "words I added: decisions, and, actions, own"
)


def research(tmp_path: Path, *criteria: object, elicitation: object = None) -> dict[str, object]:
    """The shipped research blueprint with its deliverable inside the allowed root, the given task criteria and (when given) the user's words."""
    (tmp_path / "deliverables").mkdir(exist_ok=True)
    bp = yaml.safe_load(EXAMPLE.read_text())
    bp["needs"]["deliverable"]["path"] = str(tmp_path / "deliverables" / "competitors.md")
    bp["task"]["acceptance"] = list(criteria)
    if elicitation is not None:
        bp["needs"]["elicitation"] = elicitation
    return bp


def block(bp: dict[str, object], tmp_path: Path) -> str:
    return bpm.plan_for_user(bp, allowed_roots=[tmp_path])


def details(bp: dict[str, object], tmp_path: Path) -> str:
    return bpm.render_plan(bp, allowed_roots=[tmp_path])


def test_a_from_criterion_shows_the_quote_the_question_and_the_words_root_added(tmp_path: Path) -> None:
    bp = research(tmp_path, {"text": "Every row has a date and a name.", "from": "every ROW", "asked": ASKED}, elicitation="Dates: every row.")
    for text in (block(bp, tmp_path), details(bp, tmp_path)):
        assert f'  1. Every row has a date and a name.\n     from your words "every ROW" (my question: "{ASKED}"); words I added: has, a, date, and, name' in text
    no_question = research(tmp_path, {"text": "Every row has a date.", "from": "Every row"}, elicitation="Every row")
    assert '     from your words "Every row"; words I added: has, a, date\n' in block(no_question, tmp_path) + "\n"


def test_added_words_show_up_to_8_then_plus_k_more(tmp_path: Path) -> None:
    ten = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    bp = research(tmp_path, {"text": f"quoted {ten}", "from": "quoted"}, elicitation="quoted")
    assert "words I added: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, +2 more" in block(bp, tmp_path)
    nine = research(tmp_path, {"text": "quoted alpha bravo charlie delta echo foxtrot golf hotel", "from": "quoted"}, elicitation="quoted")
    assert "words I added: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel\n" in block(nine, tmp_path) + "\n"
    none = research(tmp_path, {"text": "Quoted.", "from": "quoted"}, elicitation="quoted")
    assert "words I added: none" in block(none, tmp_path)


def test_a_default_criterion_shows_my_default_you_did_not_say_this(tmp_path: Path) -> None:
    bp = research(tmp_path, {"text": "At most 1500 words as counted by read.", "default": True}, elicitation="A short note.")
    for text in (block(bp, tmp_path), details(bp, tmp_path)):
        assert "  1. At most 1500 words as counted by read.\n     my default: you did not say this" in text


def test_a_string_criterion_shows_my_wording_your_words_were_not_recorded(tmp_path: Path) -> None:
    bp = research(tmp_path, "At most 1500 words as counted by read.", {"text": "Cite 2 sources per claim.", "default": True}, elicitation="A short note.")
    for text in (block(bp, tmp_path), details(bp, tmp_path)):
        assert "  1. At most 1500 words as counted by read.\n     my wording: your words for it were not recorded\n  2. Cite 2 sources per claim." in text


def test_a_service_criterion_shows_its_line_in_the_block_and_in_the_details(tmp_path: Path) -> None:
    sv = {"name": "brief", "description": "d", "acceptance": ["At most 600 words as counted by read.", {"text": "Cite 2 sources.", "default": True}]}
    bp = research(tmp_path)
    bp["services"], bp["task"] = [sv], {"service": "brief", "inputs": {}}
    assert "    1. At most 600 words as counted by read.\n       my wording: your words for it were not recorded\n    2. Cite 2 sources.\n       my default" in block(bp, tmp_path)
    assert "    1. At most 600 words as counted by read.\n       my wording: your words for it were not recorded\n    2. Cite 2 sources.\n       my default" in details(bp, tmp_path)


def test_a_string_criterion_is_a_criterion_source_warning() -> None:
    issues = sourcing(plain("At most 1500 words as counted by read.", {"text": "Cite 2 sources.", "default": True}, "And this one, too."))
    assert [(i.level, i.path, i.code) for i in issues if i.code == "criterion-source"] == [
        ("warning", "task.acceptance[1]", "criterion-source"), ("warning", "task.acceptance[3]", "criterion-source"),
    ]
    assert issues[0].message == (
        "criterion 1 does not say where it comes from: give from: <the user's exact words in needs.elicitation> or default: true."
    )
    sourceless = sourcing(serviced({"text": "Only text."}))
    assert [(i.level, i.path, i.code) for i in sourceless] == [("warning", "services[brief].acceptance[1]", "criterion-source")]


def test_criteria_without_needs_elicitation_are_a_criterion_words_warning() -> None:
    words = (
        "this plan records none of the user's words, so no criterion can show where it comes from. Put their answers, verbatim, in "
        "needs.elicitation (for a plan with only defaults: their request in their words), and give each criterion from: or default: true."
    )
    for bp in (plain("a plain one", elicitation=None), plain({"text": "x y z w", "default": True}, elicitation=None), plain({"text": "x y z w"}, elicitation=None)):
        assert [i for i in sourcing(bp) if i.code == "criterion-words"] == [Issue("warning", "needs.elicitation", words, "criterion-words")]
    assert [i for i in sourcing(plain({"text": "x y z w", "default": True})) if i.code == "criterion-words"] == []  # the words are there
    assert [i for i in sourcing(plain(elicitation=None)) if i.code == "criterion-words"] == []  # no criterion, nothing to show
    assert [i for i in sourcing(plain({"text": "a b c d", "from_tasks": ["t-1"]}, elicitation=None), extension=True) if i.code == "criterion-words"] == []
    assert [i for i in sourcing(plain("a plain one", elicitation="  ")) if i.code == "criterion-words"] != []  # blank words are none


def test_a_plan_with_criteria_and_no_elicitation_shows_my_wording_at_the_terminal(tmp_path: Path) -> None:
    bp = research(tmp_path, "At most 1500 words as counted by read.")
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert {i.code: i.level for i in issues if i.code.startswith("criterion-")} == {"criterion-source": "warning", "criterion-words": "warning"}
    assert not bpm.errors(issues)
    assert "     my wording: your words for it were not recorded" in details(bp, tmp_path)
    assert "criterion 1 does not say where it comes from" in details(bp, tmp_path)


def test_p1s_case_reads_the_line_of_10_1_step_4_exactly(tmp_path: Path) -> None:
    bp = research(
        tmp_path, {"text": "decisions and actions use the notes' own words", "from": "Use the words from the notes.", "asked": ASKED},
        elicitation=P1_WORDS,
    )
    assert f"  1. decisions and actions use the notes' own words\n     {P1_LINE}\n" in block(bp, tmp_path)
