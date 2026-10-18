"""Contract of ``CharterReader``: the files on disk, the in-memory registry and the lenient decorator pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import CharterReader
from orgmcp.agents.testing import IMPLEMENTATIONS, AgentsHarness

from ._support import agent, make

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-agents")

ROOT_CHARTER = ({"role": "human (root of the organization)"}, "")


@pytest.fixture(params=IMPLEMENTATIONS[CharterReader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AgentsHarness:
    made = make(request, tmp_path)
    assert isinstance(made.charters, CharterReader)
    return made


# ------------------------------------------------------------------------------ charter


@pytest.mark.parametrize("spelling", ["root", "", " ", "/", "root/", None])
def test_root_has_a_fixed_charter_under_every_spelling(h: AgentsHarness, spelling: str | None) -> None:
    assert h.charters.charter(spelling) == ROOT_CHARTER  # type: ignore[arg-type]


def test_roots_charter_does_not_come_from_a_file(h: AgentsHarness) -> None:
    h.put("AGENT.md", "---\nrole: not root's\n---\nbody\n")
    assert h.charters.charter("root") == ROOT_CHARTER


def test_the_charter_is_the_frontmatter_and_the_stripped_body(h: AgentsHarness) -> None:
    agent(h, "ceo")
    meta, body = h.charters.charter("ceo")
    assert meta == {"role": "Researcher", "tools": ["read"]}
    assert body == "# Role: Researcher\n\nFind things out."


def test_the_body_is_stripped_at_both_ends_and_the_inside_is_kept(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "---\nrole: R\n---\n\n\n   First  line\n\n\n  Last line   \n\n\n")
    assert h.charters.charter("ceo")[1] == "First  line\n\n\n  Last line"


def test_the_frontmatter_keeps_its_types(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "---\nrole: R\ncan_hire: true\nmax_children: 3\nmodel: null\ninputs: []\nworkspace: /w/x\n---\nb\n")
    assert h.charters.charter("ceo")[0] == {
        "role": "R", "can_hire": True, "max_children": 3, "model": None, "inputs": [], "workspace": "/w/x"
    }


def test_a_charter_without_frontmatter_is_all_body(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "\n  Just words.  \n")
    assert h.charters.charter("ceo") == ({}, "Just words.")


def test_a_frontmatter_that_is_not_a_mapping_is_empty(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "---\n- a\n- b\n---\nbody\n")
    assert h.charters.charter("ceo") == ({}, "body")


def test_the_text_may_be_unicode(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "---\nrole: Étudiante ✓\n---\n日本語 é\n")
    assert h.charters.charter("ceo") == ({"role": "Étudiante ✓"}, "日本語 é")


def test_an_address_is_normalized_before_it_is_read(h: AgentsHarness) -> None:
    agent(h, "ceo/eng")
    assert h.charters.charter(" /ceo/eng/ ")[0]["role"] == "Researcher"


def test_a_changed_charter_is_read_again(h: AgentsHarness) -> None:
    agent(h, "ceo")
    assert h.charters.charter("ceo")[0]["role"] == "Researcher"
    h.put("ceo/AGENT.md", "---\nrole: Boss\n---\nnew words, a different size\n")
    assert h.charters.charter("ceo") == ({"role": "Boss"}, "new words, a different size")


def test_a_charter_that_is_missing_is_an_error_or_the_placeholder(h: AgentsHarness) -> None:
    if h.lenient:
        assert h.charters.charter("ghost") == ({"role": "?"}, "")
    else:
        with pytest.raises(FileNotFoundError):
            h.charters.charter("ghost")


def test_a_frontmatter_that_does_not_parse_is_an_error_or_the_placeholder(h: AgentsHarness) -> None:
    h.put("ceo/AGENT.md", "---\nrole: [unclosed\n---\nbody\n")
    if h.lenient:
        assert h.charters.charter("ceo") == ({"role": "?"}, "")
    else:
        with pytest.raises(Exception) as raised:
            h.charters.charter("ceo")
        assert type(raised.value).__name__ in {"ParserError", "ScannerError"}


# ------------------------------------------------------------------------------ memory


def test_memory_is_the_text_exactly_as_written(h: AgentsHarness) -> None:
    text = "  # Notes é\n\nline two   \n\n\n"
    h.put("ceo/MEMORY.md", text)
    assert h.charters.memory("ceo") == text


def test_an_empty_memory_is_empty(h: AgentsHarness) -> None:
    h.put("ceo/MEMORY.md", "")
    assert h.charters.memory("ceo") == ""


def test_a_missing_memory_is_empty(h: AgentsHarness) -> None:
    agent(h, "ceo")
    assert h.charters.memory("ceo") == ""
    assert h.charters.memory("nobody") == ""


def test_a_memory_that_is_a_directory_is_empty(h: AgentsHarness) -> None:
    h.put_dir("ceo/MEMORY.md")
    assert h.charters.memory("ceo") == ""


def test_roots_memory_is_the_file_in_the_organization_directory(h: AgentsHarness) -> None:
    h.put("MEMORY.md", "root notes\n")
    assert h.charters.memory("root") == "root notes\n"
    assert h.charters.memory("") == "root notes\n"


def test_a_memory_of_an_agent_is_its_own(h: AgentsHarness) -> None:
    h.put("ceo/MEMORY.md", "ceo\n")
    h.put("ceo/eng/MEMORY.md", "eng\n")
    assert (h.charters.memory("ceo"), h.charters.memory("ceo/eng"), h.charters.memory(" /ceo/eng/ ")) == ("ceo\n", "eng\n", "eng\n")


def test_a_changed_memory_is_read_again(h: AgentsHarness) -> None:
    h.put("ceo/MEMORY.md", "one\n")
    assert h.charters.memory("ceo") == "one\n"
    h.put("ceo/MEMORY.md", "two\n")
    assert h.charters.memory("ceo") == "two\n"

