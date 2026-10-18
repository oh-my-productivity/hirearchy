"""Contract of ``SkillSource``: the packaged text, read fresh each time; the real source and its in-memory model pass the same tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.skill import SkillSource
from orgmcp.skill.testing import IMPLEMENTATIONS, SourceHarness

MESSAGE = "the orgmcp skill file was not found in this installation (expected skills/orgmcp/SKILL.md)"


@pytest.fixture(params=IMPLEMENTATIONS[SkillSource], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SourceHarness:
    made = cast(Callable[[Path], SourceHarness], request.param)(tmp_path)
    assert isinstance(made.source, SkillSource)
    return made


def test_the_packaged_text(h: SourceHarness) -> None:
    h.provide("---\nname: orgmcp\n---\nbody\n")
    assert h.source.read() == "---\nname: orgmcp\n---\nbody\n"


def test_the_text_is_utf8_and_keeps_its_line_endings(h: SourceHarness) -> None:
    h.provide("naïve ✓\n\nlast line without newline")
    assert h.source.read() == "naïve ✓\n\nlast line without newline"


def test_a_missing_skill_is_an_org_error_with_the_fixed_text(h: SourceHarness) -> None:
    with pytest.raises(OrgError) as raised:
        h.source.read()
    assert str(raised.value) == MESSAGE


def test_the_text_is_read_again_on_every_call(h: SourceHarness) -> None:
    h.provide("first\n")
    assert h.source.read() == "first\n"
    h.provide("second\n")
    assert h.source.read() == "second\n"
    h.remove()
    with pytest.raises(OrgError):
        h.source.read()
    h.provide("third\n")
    assert h.source.read() == "third\n"
