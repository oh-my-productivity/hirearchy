"""The text heuristics and small predicates of the rules of ``validate``: each answers what the flat module's private function answered
(the expected values were captured from ``blueprint._legacy`` before the rules moved)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint._rules import (
    blob,
    delivers_directly,
    edits_others_files,
    has_ws_tools,
    is_code,
    review_required,
    vague,
)
from orgmcp.blueprint.api import Agent, Issue




def agent(**kw: object) -> Agent:
    values: dict[str, object] = {"addr": "a", "name": "a", "parent": None, "where": "w"}
    values.update(kw)
    return Agent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("text, hit", [
    ("Apply the corrections directly to the report.", "Apply the corrections directly to the report"),
    ("Fix it in place", "Fix it in place"),
    ("make the changes to the draft", "make the changes to the draft"),
    ("correct the text directly", "correct the text directly"),
    ("overwrite the deliverable", "overwrite the deliverable"),
    ("Never edit the report.", None),  # a negated phrase is fine
    ("do not modify the file directly", None),
    ("The reviewer reports findings; the author applies them.", None),
    ("update it directly", None),
    ("Check every claim.", None),
])
def test_the_phrase_that_tells_someone_to_change_another_agents_file(text: str, hit: str | None) -> None:
    assert edits_others_files(text) == hit


@pytest.mark.parametrize("bp, expected", [
    ({}, False),
    ({"needs": {"kind": "code"}}, True),
    ({"mission": "software library", "needs": {"kind": "Writing"}}, False),  # an explicit kind decides, in either case
    ({"mission": "Build a CLI"}, True),
    ({"mission": "Write a memo"}, False),
    ({"mission": "decoder"}, False),  # whole words only
    ({"task": {"goal": "refactor the repo"}}, True),
    ({"services": [{"description": "implement a feature"}]}, True),
    ({"services": [{"deliverable": {"format": "python package"}}]}, True),
])
def test_a_goal_is_code_when_its_kind_says_so_or_its_words_do(bp: dict[str, object], expected: bool) -> None:
    assert is_code(bp) is expected


def test_the_blob_is_what_the_blueprint_promises_one_item_per_line() -> None:
    bp = {"mission": "M", "needs": {"scope": "S", "sources": "SRC", "quality_bar": "Q", "deliverable": {"description": "D", "format": "F"}},
          "task": {"goal": "G", "acceptance": ["a1", " ", "a2"]},
          "services": [{"description": "SD", "deliverable": "SDD", "acceptance": ["s1", "", "s2"],
                        "inputs": [{"description": "ID1"}, "x", {"name": "n"}]}, "junk"]}
    assert blob(bp) == "M\nS\nSRC\nQ\nD\nF\nG\na1\na2\nSD\nSDD\ns1\ns2\nID1"
    assert blob({}) == ""


@pytest.mark.parametrize("value, expected", [
    (None, None), ("", None), (True, True), (False, False), ("yes", True), ("nothing", True), (0, True),
    ("no, skip it", False), ("None needed", False), ("false", False), ("Not required", False), ("skip", False), ("NO", False),
])
def test_review_is_decided_true_false_or_not_at_all(value: object, expected: bool | None) -> None:
    assert review_required({"review": value}) is expected


def test_review_not_mentioned_is_not_decided() -> None:
    assert review_required({}) is None


@pytest.mark.parametrize("tools, expected", [([], False), (["write"], False), (["shell"], False), (["write", "shell"], True), (["write", "shell", "read"], True)])
def test_only_write_and_shell_together_can_deliver_files(tools: list[str], expected: bool) -> None:
    assert has_ws_tools(agent(tools=tools)) is expected


def test_vague_criteria_are_warned_about_with_their_position() -> None:
    issues: list[Issue] = []
    vague(["Good quality", "At most 600 words", "every section has a table row", "Be thorough and clear", "Write 3 clear paragraphs here",
           "short one", "Use `uv run pytest` always"], "task.acceptance", issues)
    assert [(i.level, i.path, i.code) for i in issues] == [("warning", "task.acceptance[1]", "vague-criterion"), ("warning", "task.acceptance[4]", "vague-criterion"),
                                                           ("warning", "task.acceptance[6]", "vague-criterion")]
    assert issues[0].message == "'Good quality' is not checkable; state the exact number, section, format or path that decides pass/fail"


def test_only_an_author_with_write_and_shell_inside_whose_workspace_the_path_is_delivers_directly() -> None:
    agents = [agent(addr="w", tools=["write", "shell"], workspace="/ws", kind="author"),
              agent(addr="v", tools=["write", "shell"], workspace="/ws2", kind="verifier"),
              agent(addr="r", tools=["read"], workspace="/ws3", kind="author")]
    assert [delivers_directly(agents, Path(p)) for p in ("/ws", "/ws/out/x.md", "/ws2/x", "/ws3/x", "/ws-other/x", "/elsewhere")] == \
        [True, True, False, False, False, False]
