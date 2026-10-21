"""The pure parts of an ORG.md: the frontmatter as written, the body, and the mission inside it."""

from __future__ import annotations

import pytest

from hirearchy.kernel import OrgError
from hirearchy.templates.testing import static_document_templates
from hirearchy.upgrade._rules import MISSION_HEADING, RULES_HEADING, extract_mission, split_raw

from ._cases import MISSION


def test_split_raw_keeps_the_frontmatter_exactly_as_written() -> None:
    text = "---\n# comment\na:   1\n---\nbody\n"
    assert split_raw(text) == ("---\n# comment\na:   1\n---\n", "body\n")
    assert "".join(split_raw(text)) == text


@pytest.mark.parametrize("text", ["body only\n", "---\nnever closed\n", "", "--- not a fence\n---\n"])
def test_split_raw_of_a_text_without_a_frontmatter_block_is_all_body(text: str) -> None:
    assert split_raw(text) == ("", text)


def test_the_headings_are_those_of_the_rules_template() -> None:
    rules = static_document_templates().org_rules(MISSION)
    assert MISSION_HEADING in rules and RULES_HEADING in rules


def test_the_mission_keeps_the_headings_that_are_inside_it() -> None:
    assert extract_mission(static_document_templates().org_rules(MISSION)) == MISSION


def test_the_mission_ends_at_the_next_level_two_heading_when_the_rules_heading_was_edited_away() -> None:
    body = "# Org\n\n## Mission\nStudy things.\n\n## Something else\nmine\n"
    assert extract_mission(body) == "Study things."


def test_the_mission_runs_to_the_end_when_nothing_follows_it() -> None:
    assert extract_mission("## Mission\n\n  Study things.  \n") == "Study things."


def test_a_body_without_a_mission_section_cannot_be_upgraded() -> None:
    with pytest.raises(OrgError, match="no '## Mission' section, so the rules cannot be upgraded automatically; edit ORG.md by hand"):
        extract_mission("My own rules.\n")
