"""Contract of ``IssueText``: what an issue says of itself (a pure function of its data, so one implementation)."""

from __future__ import annotations

import dataclasses

import pytest

from orgmcp.blueprint import Issue, IssueText, errors


def test_an_issue_is_an_issue_text() -> None:
    assert isinstance(Issue("error", "mission", "write it"), IssueText)


def test_it_renders_level_path_and_message() -> None:
    assert Issue("error", "needs.deliverable", "state the deliverable", "deliverable").render() == "error: needs.deliverable: state the deliverable"
    assert Issue("warning", "", "no path").render() == "warning: : no path"


def test_the_code_is_not_part_of_the_text_and_defaults_to_empty() -> None:
    assert Issue("warning", "p", "m").code == "" and Issue("warning", "p", "m", "c").render() == Issue("warning", "p", "m").render()


def test_an_issue_is_a_value() -> None:
    issue = Issue("error", "p", "m", "c")
    assert issue == Issue("error", "p", "m", "c") and hash(issue) == hash(Issue("error", "p", "m", "c"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        issue.level = "warning"  # type: ignore[misc]


def test_only_the_errors_block_apply() -> None:
    issues = [Issue("warning", "a", "x"), Issue("error", "b", "y"), Issue("warning", "c", "z"), Issue("error", "d", "w")]
    assert errors(issues) == [issues[1], issues[3]] and errors([]) == [] and errors(issues[:1]) == []
