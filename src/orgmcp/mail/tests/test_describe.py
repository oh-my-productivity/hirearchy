"""``describe``: the front matter of the text of a message file and what is wrong with it (what ``FsMessageIndex`` reports per file)."""

from __future__ import annotations

import pytest

from orgmcp.mail._index import describe

from ._support import BAD_YAML


@pytest.mark.parametrize(
    ("text", "meta", "error"),
    [
        ("---\nfrom: root\nto: ceo\ntype: note\n---\nx\n", {"from": "root", "to": "ceo", "type": "note"}, None),
        ("---\nfrom: root\nto: ceo\ntype: note\nbudget: 0\n---\nx\n", {"from": "root", "to": "ceo", "type": "note", "budget": 0}, None),
        ("---\nfrom: root\nto: ceo\ntype: note\nbudget: '3'\n---\nx\n", {"from": "root", "to": "ceo", "type": "note", "budget": "3"}, None),
        ("plain\n", {}, "no frontmatter"),
        ("---\nfrom: root\n---\nx\n", {"from": "root"}, "frontmatter lacks from/to/type"),
        ("---\nfrom: root\nto: ceo\ntype: task\nbudget: lots\n---\nx\n", {"from": "root", "to": "ceo", "type": "task", "budget": "lots"},
         "budget is not a number: 'lots'"),
    ],
)
def test_describe(text: str, meta: dict[str, object], error: str | None) -> None:
    assert describe(text) == (meta, error)


def test_describe_of_a_front_matter_that_does_not_parse() -> None:
    assert describe(BAD_YAML) == (None, "frontmatter does not parse (ParserError)")
