"""Contract of ``AgentRegistry``: the files on disk and the in-memory registry pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import AgentRegistry
from hirearchy.agents.testing import IMPLEMENTATIONS, AgentsHarness
from hirearchy.kernel import join_frontmatter

from ._support import agent, make

SKELETON = ["AGENT.md", "MEMORY.md", "inbox", "inflight", "read", "runs", "sent", "work"]
META = {"role": "Engineer", "model": "m-1", "tools": ["read", "write"], "can_hire": False, "max_children": 5, "hired_by": "ceo"}


@pytest.fixture(params=IMPLEMENTATIONS[AgentRegistry], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AgentsHarness:
    made = make(request, tmp_path)
    assert isinstance(made.registry, AgentRegistry)
    return made


# ------------------------------------------------------------------------------ create


def test_create_makes_the_skeleton_an_empty_memory_and_the_charter(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "# Role: Engineer\n\nBuild.")
    assert h.listing("ceo") == SKELETON
    for box in ("inbox", "inflight", "read", "sent", "work", "runs"):
        assert h.listing(f"ceo/{box}") == []
    assert h.read("ceo/MEMORY.md") == ""


def test_the_charter_is_the_frontmatter_in_its_order_and_the_text(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "# Role: Engineer\n\nBuild.")
    assert h.read("ceo/AGENT.md") == join_frontmatter(dict(META), "# Role: Engineer\n\nBuild.")
    assert h.read("ceo/AGENT.md") == (
        "---\nrole: Engineer\nmodel: m-1\ntools:\n- read\n- write\ncan_hire: false\nmax_children: 5\nhired_by: ceo\n---\n"
        "# Role: Engineer\n\nBuild.\n"
    )


def test_the_charter_text_ends_with_exactly_one_newline(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "R"}, "text\n\n\n")
    assert h.read("ceo/AGENT.md") == "---\nrole: R\n---\ntext\n"


def test_unicode_survives(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "Étudiante ✓"}, "日本語 é")
    assert h.read("ceo/AGENT.md") == "---\nrole: Étudiante ✓\n---\n日本語 é\n"


def test_a_created_agent_exists_and_has_its_charter(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "# Role\n\nBuild.")
    assert h.directory.exists("ceo") is True and h.directory.agents() == ["ceo"]
    assert h.charters.charter("ceo") == (META, "# Role\n\nBuild.")
    assert h.charters.memory("ceo") == ""


def test_an_agent_is_created_below_its_parent(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "Boss"}, "x")
    h.registry.create("ceo/eng", {"role": "Eng"}, "y")
    assert h.listing("ceo/eng") == SKELETON
    assert h.directory.children("ceo") == ["ceo/eng"] and h.directory.agents() == ["ceo", "ceo/eng"]
    assert h.listing("ceo") == sorted([*SKELETON, "eng"])


def test_the_address_is_normalized(h: AgentsHarness) -> None:
    h.registry.create(" /ceo/ ", {"role": "R"}, "x")
    assert h.listing("ceo") == SKELETON


def test_creating_one_agent_leaves_the_others_alone(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "A"}, "a")
    h.put("ceo/MEMORY.md", "ceo's notes\n")
    h.registry.create("cto", {"role": "B"}, "b")
    assert h.read("ceo/MEMORY.md") == "ceo's notes\n" and h.read("ceo/AGENT.md") == "---\nrole: A\n---\na\n"


def test_every_key_of_the_meta_is_written_and_read_back(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "R", "inputs": [], "workspace": "/w", "created": "2026-10-18T10:00:00+00:00"}, "x")
    assert h.charters.charter("ceo")[0] == {"role": "R", "inputs": [], "workspace": "/w", "created": "2026-10-18T10:00:00+00:00"}


# ------------------------------------------------------------------------------ rewrite_charter


def test_a_rewrite_replaces_the_charter_exactly(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "old")
    h.registry.rewrite_charter("ceo", "---\nrole: New\n---\n  new text, no newline at the end")
    assert h.read("ceo/AGENT.md") == "---\nrole: New\n---\n  new text, no newline at the end"
    assert h.charters.charter("ceo") == ({"role": "New"}, "new text, no newline at the end")


def test_a_rewrite_touches_nothing_else(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "old")
    h.put("ceo/MEMORY.md", "notes\n")
    h.put("ceo/work/draft.md", "draft\n")
    h.registry.create("ceo/eng", {"role": "E"}, "e")
    h.registry.rewrite_charter("ceo", "---\nrole: New\n---\nx\n")
    assert h.listing("ceo") == sorted([*SKELETON, "eng"])
    assert (h.read("ceo/MEMORY.md"), h.read("ceo/work/draft.md")) == ("notes\n", "draft\n")
    assert h.read("ceo/eng/AGENT.md") == "---\nrole: E\n---\ne\n"


def test_a_rewrite_of_an_agent_that_is_not_there_creates_the_charter_file(h: AgentsHarness) -> None:
    h.registry.rewrite_charter("ceo", "---\nrole: R\n---\nx\n")
    assert h.read("ceo/AGENT.md") == "---\nrole: R\n---\nx\n"


def test_a_rewrite_accepts_any_text_unicode_included(h: AgentsHarness) -> None:
    h.registry.rewrite_charter("ceo", "é ✓\nno frontmatter at all")
    assert h.read("ceo/AGENT.md") == "é ✓\nno frontmatter at all"


# ------------------------------------------------------------------------------ archive


def test_archive_moves_the_whole_directory_below_retired(h: AgentsHarness) -> None:
    h.registry.create("ceo", META, "x")
    h.put("ceo/MEMORY.md", "notes\n")
    h.put("ceo/work/draft.md", "draft\n")
    h.put("ceo/runs/20260101T000000000000.log", "log\n")
    name = h.registry.archive("ceo", "20261018T101500")
    assert name == "ceo-20261018T101500"
    assert h.listing("ceo") is None and h.directory.exists("ceo") is False and h.directory.agents() == []
    assert h.listing(".retired") == ["ceo-20261018T101500"]
    assert h.listing(".retired/ceo-20261018T101500") == SKELETON
    assert h.read(".retired/ceo-20261018T101500/MEMORY.md") == "notes\n"
    assert h.read(".retired/ceo-20261018T101500/work/draft.md") == "draft\n"
    assert h.read(".retired/ceo-20261018T101500/AGENT.md") == join_frontmatter(dict(META), "x")


def test_archive_takes_the_agents_below_along(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "Boss"}, "x")
    h.registry.create("ceo/eng", {"role": "Eng"}, "y")
    h.registry.create("ceo/eng/qa", {"role": "QA"}, "z")
    h.registry.archive("ceo", "S1")
    assert h.read(".retired/ceo-S1/eng/qa/AGENT.md") == "---\nrole: QA\n---\nz\n"
    assert h.directory.agents() == []


def test_the_name_of_a_nested_agent_has_a_dot_for_each_slash(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "Boss"}, "x")
    h.registry.create("ceo/eng", {"role": "Eng"}, "y")
    h.registry.create("ceo/eng/qa", {"role": "QA"}, "z")
    assert h.registry.archive("ceo/eng/qa", "20261018T101500") == "ceo.eng.qa-20261018T101500"
    assert h.registry.archive("ceo/eng", "20261018T101501") == "ceo.eng-20261018T101501"
    assert h.listing(".retired") == ["ceo.eng-20261018T101501", "ceo.eng.qa-20261018T101500"]
    assert h.directory.agents() == ["ceo"] and h.directory.children("ceo") == []


def test_archiving_one_agent_leaves_its_siblings_and_its_parent(h: AgentsHarness) -> None:
    for addr in ("ceo", "ceo/a", "ceo/b", "cto"):
        agent(h, addr)
    h.registry.archive("ceo/a", "S")
    assert h.directory.agents() == ["ceo", "ceo/b", "cto"]
    assert h.listing(".retired") == ["ceo.a-S"]


def test_archive_creates_the_retired_directory_when_it_is_the_first(h: AgentsHarness) -> None:
    agent(h, "ceo")
    assert h.listing(".retired") is None
    h.registry.archive("ceo", "S")
    assert h.listing(".retired") == ["ceo-S"]


def test_archive_adds_to_the_retired_directory(h: AgentsHarness) -> None:
    agent(h, "ceo")
    agent(h, "cto")
    h.registry.archive("ceo", "S1")
    h.registry.archive("cto", "S2")
    assert h.listing(".retired") == ["ceo-S1", "cto-S2"]


def test_the_address_is_normalized_when_archiving(h: AgentsHarness) -> None:
    agent(h, "ceo/eng")
    assert h.registry.archive(" /ceo/eng/ ", "S") == "ceo.eng-S"


def test_archiving_an_agent_that_is_not_there_is_an_error_and_changes_nothing(h: AgentsHarness) -> None:
    agent(h, "cto")
    with pytest.raises(FileNotFoundError):
        h.registry.archive("ceo", "S")
    assert h.directory.agents() == ["cto"]


def test_a_second_archive_with_the_same_name_puts_the_agent_inside_the_first(h: AgentsHarness) -> None:
    """What ``shutil.move`` always did when the destination exists (the same agent hired and retired again within a second)."""
    h.registry.create("ceo", {"role": "first"}, "1")
    assert h.registry.archive("ceo", "S") == "ceo-S"
    h.registry.create("ceo", {"role": "second"}, "2")
    assert h.registry.archive("ceo", "S") == "ceo-S"
    assert h.listing(".retired") == ["ceo-S"]
    assert h.read(".retired/ceo-S/AGENT.md") == "---\nrole: first\n---\n1\n"
    assert h.read(".retired/ceo-S/ceo/AGENT.md") == "---\nrole: second\n---\n2\n"


def test_an_archived_agent_can_be_created_again(h: AgentsHarness) -> None:
    h.registry.create("ceo", {"role": "first"}, "1")
    h.registry.archive("ceo", "S")
    h.registry.create("ceo", {"role": "second"}, "2")
    assert h.charters.charter("ceo") == ({"role": "second"}, "2")
    assert h.read(".retired/ceo-S/AGENT.md") == "---\nrole: first\n---\n1\n"
