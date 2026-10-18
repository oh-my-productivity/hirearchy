"""Contract of ``AgentDirectory``: the directories on disk, the in-memory registry and the caching decorator pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.agents.testing import IMPLEMENTATIONS, AgentsHarness
from orgmcp.kernel import RESERVED, OrgError

from ._support import agent, make


@pytest.fixture(params=IMPLEMENTATIONS[AgentDirectory], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AgentsHarness:
    made = make(request, tmp_path)
    assert isinstance(made.directory, AgentDirectory)
    return made


@pytest.fixture
def team(h: AgentsHarness) -> AgentsHarness:
    """root > ceo > {a > x, b}; root > cto."""
    for addr in ("ceo", "ceo/a", "ceo/a/x", "ceo/b", "cto"):
        agent(h, addr)
    return h


# ------------------------------------------------------------------------------ exists


@pytest.mark.parametrize("spelling", ["root", "", " ", "/", "root/", " root ", "\nroot\n", "//root//"])
def test_root_exists_in_an_empty_organization_under_every_spelling(h: AgentsHarness, spelling: str) -> None:
    assert h.directory.exists(spelling) is True


def test_root_exists_for_none(h: AgentsHarness) -> None:
    assert h.directory.exists(None) is True  # type: ignore[arg-type]


def test_an_agent_exists_when_its_charter_is_a_file(team: AgentsHarness) -> None:
    assert [team.directory.exists(a) for a in ("ceo", "ceo/a", "ceo/a/x", "ceo/b", "cto")] == [True] * 5


def test_an_address_is_normalized_before_it_is_looked_up(team: AgentsHarness) -> None:
    assert team.directory.exists(" /ceo/a/ ") is True
    assert team.directory.exists("ceo/a\n") is True


def test_a_directory_without_a_charter_is_no_agent(h: AgentsHarness) -> None:
    h.put_dir("ghost")
    h.put("ghost/inbox/m.md", "x")
    assert h.directory.exists("ghost") is False


def test_a_charter_that_is_a_directory_is_no_charter(h: AgentsHarness) -> None:
    h.put_dir("odd/AGENT.md")
    assert h.directory.exists("odd") is False


def test_exists_looks_at_the_names_and_the_charter_of_the_agent_only(h: AgentsHarness) -> None:
    agent(h, "ceo/eng")  # ceo itself has no charter
    assert h.directory.exists("ceo/eng") is True  # only the names are checked, not the parents' charters
    assert h.directory.exists("ceo") is False


def test_a_missing_agent_does_not_exist(team: AgentsHarness) -> None:
    assert team.directory.exists("nobody") is False
    assert team.directory.exists("ceo/nobody") is False


@pytest.mark.parametrize(
    "addr",
    ["Ceo", "ceo/Eng", "1ceo", "-ceo", "ce_o", "ce o", "ceo//eng", "ceo/./eng", "..", "../ceo", "ceo/..", "a" * 33, "ceo/" + "a" * 33,
     "ceo/ops\n/x", "ceo/\nops/x", "ceo/ops\r/x", "ceo/ops\t/x", "ceo/é", ".hidden", "ceo/.hidden"],
)
def test_names_must_match_the_name_rules_even_when_the_charter_is_there(h: AgentsHarness, addr: str) -> None:
    h.put(f"{addr}/AGENT.md", "---\nrole: R\n---\nx\n")
    assert h.directory.exists(addr) is False


def test_a_name_of_the_longest_allowed_length_is_valid(h: AgentsHarness) -> None:
    agent(h, "a" * 32)
    agent(h, "ceo/" + "z" * 32)
    assert h.directory.exists("a" * 32) is True
    assert h.directory.exists("ceo/" + "z" * 32) is True


@pytest.mark.parametrize("reserved", sorted(RESERVED - {"root"}))
def test_a_reserved_name_is_no_agent_at_any_depth(h: AgentsHarness, reserved: str) -> None:
    h.put(f"{reserved}/AGENT.md", "---\nrole: R\n---\nx\n")
    h.put(f"ceo/{reserved}/AGENT.md", "---\nrole: R\n---\nx\n")
    assert h.directory.exists(reserved) is False
    assert h.directory.exists(f"ceo/{reserved}") is False


# ------------------------------------------------------------------------------ require


def test_require_returns_the_normalized_address(team: AgentsHarness) -> None:
    assert team.directory.require(" /ceo/a/ ") == "ceo/a"
    assert team.directory.require("ceo") == "ceo"
    assert team.directory.require("") == "root"
    assert team.directory.require("root/") == "root"


def test_require_of_a_missing_agent_names_the_normalized_address(team: AgentsHarness) -> None:
    with pytest.raises(OrgError) as raised:
        team.directory.require(" /zz/ ")
    assert str(raised.value) == "no such agent: zz"


def test_require_of_an_invalid_name_is_the_same_error(team: AgentsHarness) -> None:
    with pytest.raises(OrgError, match="no such agent: Ceo"):
        team.directory.require("Ceo")


# ------------------------------------------------------------------------------ children


def test_the_children_of_root_are_the_top_level_agents_sorted(team: AgentsHarness) -> None:
    assert team.directory.children("root") == ["ceo", "cto"]
    assert team.directory.children("") == ["ceo", "cto"]


def test_the_children_of_an_agent_are_its_direct_reports_with_full_addresses(team: AgentsHarness) -> None:
    assert team.directory.children("ceo") == ["ceo/a", "ceo/b"]
    assert team.directory.children("ceo/a") == ["ceo/a/x"]
    assert team.directory.children(" /ceo/ ") == ["ceo/a", "ceo/b"]


def test_an_agent_without_reports_has_no_children(team: AgentsHarness) -> None:
    assert team.directory.children("cto") == []
    assert team.directory.children("ceo/a/x") == []


def test_the_children_of_a_missing_agent_are_none(team: AgentsHarness) -> None:
    assert team.directory.children("nobody") == []


def test_children_are_sorted_by_name(h: AgentsHarness) -> None:
    for name in ("zed", "alpha", "mid", "alpha-2", "a1"):
        agent(h, name)
    assert h.directory.children("root") == ["a1", "alpha", "alpha-2", "mid", "zed"]


def test_only_directories_with_a_charter_and_a_valid_unreserved_name_are_children(h: AgentsHarness) -> None:
    agent(h, "real")
    h.put_dir("empty")  # no charter
    h.put("file-only", "---\nrole: R\n---\n")  # a file, not a directory
    h.put("Upper/AGENT.md", "x")
    h.put("with space/AGENT.md", "x")
    h.put("work/AGENT.md", "x")
    h.put("inbox/AGENT.md", "x")
    h.put(".retired/old-20260101T000000/AGENT.md", "x")
    h.put("ops\n/AGENT.md", "x")
    assert h.directory.children("root") == ["real"]


def test_a_changed_tree_is_seen_by_the_next_call(h: AgentsHarness) -> None:
    agent(h, "ceo")
    assert h.directory.children("root") == ["ceo"]
    agent(h, "cto")
    assert h.directory.children("root") == ["ceo", "cto"]
    agent(h, "ceo/eng")
    assert h.directory.children("ceo") == ["ceo/eng"]
    assert h.directory.agents() == ["ceo", "ceo/eng", "cto"]


# ------------------------------------------------------------------------------ agents and subtree


def test_agents_lists_every_agent_but_root_parents_before_children(team: AgentsHarness) -> None:
    assert team.directory.agents() == ["ceo", "ceo/a", "ceo/a/x", "ceo/b", "cto"]


def test_an_organization_without_agents_has_none(h: AgentsHarness) -> None:
    assert h.directory.agents() == []


def test_the_agents_below_a_missing_charter_are_not_listed(h: AgentsHarness) -> None:
    agent(h, "ceo/eng")  # nobody is ceo
    assert h.directory.agents() == []


def test_the_subtree_starts_with_the_address_and_lists_every_agent_before_its_descendants(team: AgentsHarness) -> None:
    got = team.directory.subtree("ceo")
    assert got[0] == "ceo" and sorted(got) == ["ceo", "ceo/a", "ceo/a/x", "ceo/b"]
    assert got.index("ceo/a") < got.index("ceo/a/x")


def test_the_subtree_visits_the_siblings_in_reverse_order_like_the_org_always_did(team: AgentsHarness) -> None:
    assert team.directory.subtree("ceo") == ["ceo", "ceo/b", "ceo/a", "ceo/a/x"]
    assert team.directory.subtree("root") == ["root", "cto", "ceo", "ceo/b", "ceo/a", "ceo/a/x"]


def test_the_subtree_of_a_leaf_is_the_leaf(team: AgentsHarness) -> None:
    assert team.directory.subtree("cto") == ["cto"]
    assert team.directory.subtree(" /ceo/a/x/ ") == ["ceo/a/x"]


def test_the_subtree_of_a_missing_agent_is_just_that_address(team: AgentsHarness) -> None:
    assert team.directory.subtree("nobody") == ["nobody"]


def test_the_subtree_of_the_empty_address_is_the_root_and_everyone(team: AgentsHarness) -> None:
    assert team.directory.subtree("")[0] == "root"
    assert sorted(team.directory.subtree("")[1:]) == team.directory.agents() and len(team.directory.subtree("")) == 6
