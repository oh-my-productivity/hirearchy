"""``LiteralQuoter``: a task's body quoted verbatim, one ``> `` line per line, cut when long with the real path of the file."""

from __future__ import annotations

import pytest

from pathlib import Path

from hirearchy.kernel import RENDER_BODY_CHARS, Message, OrgPaths
from hirearchy.prompts._ports import TaskQuoter
from hirearchy.prompts._quote import LiteralQuoter


ROOT = Path("/org")


def task(body: str, path: Path | None = None) -> Message:
    return Message(sender="root", to="ceo", type="task", title="t", body=body, id="20260101T000000000001-root-aaaa", path=path)


def quoter() -> TaskQuoter:
    return LiteralQuoter(OrgPaths(ROOT))


def test_every_line_is_quoted_and_a_blank_line_has_no_trailing_space() -> None:
    assert quoter().quote(task("## Goal\nDo it.\n\n## Acceptance criteria\n33 words")) == "> ## Goal\n> Do it.\n>\n> ## Acceptance criteria\n> 33 words"


def test_the_body_is_stripped() -> None:
    assert quoter().quote(task("\n\n  body\n\n")) == "> body"


def test_a_short_body_is_not_cut() -> None:
    assert "cut" not in quoter().quote(task("x" * RENDER_BODY_CHARS))


def test_a_long_body_is_cut_with_the_path_of_the_file_relative_to_the_organization() -> None:
    quoted = quoter().quote(task("a" * (RENDER_BODY_CHARS + 10), ROOT / "ceo" / "read" / "20260101T000000000001-root-aaaa.md"))
    assert quoted.endswith('> [... message cut: 10 more of %d characters. Read the rest with read(path="ceo/read/20260101T000000000001-root-aaaa.md") if you need it.]'
                           % (RENDER_BODY_CHARS + 10))


def test_a_file_outside_the_organization_or_no_file_falls_back_to_the_box_of_the_recipient() -> None:
    body = "a" * (RENDER_BODY_CHARS + 1)
    assert 'read(path="ceo/elsewhere/x.md")' in quoter().quote(task(body, Path("/other/elsewhere/x.md")))
    assert 'read(path="ceo/<box>/20260101T000000000001-root-aaaa.md")' in quoter().quote(task(body))
