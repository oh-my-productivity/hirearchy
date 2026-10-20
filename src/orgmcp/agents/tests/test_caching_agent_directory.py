"""``CachingAgentDirectory``: the children of an agent are listed again only when the directory changed, or was changed too recently
to be trusted (the dashboard's decorator; it replaces ``LenientOrg.children``)."""

from __future__ import annotations

import pytest

from orgmcp.agents import AgentDirectory
from orgmcp.agents._caching import CACHE_TRUST, CachingAgentDirectory, DirectoryProbe
from orgmcp.agents._tree import TreeDirectory
from orgmcp.kernel import OrgError
from orgmcp.kernel.testing import FakeClock

SECOND = 1_000_000_000


class ScriptedDirectory(TreeDirectory):
    """Answers from a table and counts the questions."""

    def __init__(self) -> None:
        self.kids: dict[str, list[str]] = {"root": ["a", "b"], "a": ["a/x"]}
        self.listed: list[str] = []
        self.looked_up: list[str] = []

    def exists(self, addr: str) -> bool:
        self.looked_up.append(addr)
        return addr in ("root", "a", "b", "a/x")

    def children(self, addr: str) -> list[str]:
        self.listed.append(addr)
        return list(self.kids.get(addr, []))


class ScriptedProbe(DirectoryProbe):
    def __init__(self) -> None:
        self.mtimes: dict[tuple[str, str], int] = {}
        self.asked: list[tuple[str, str]] = []

    def mtime(self, addr: str, name: str) -> int:
        self.asked.append((addr, name))
        return self.mtimes.get((addr, name), -1)


class Setup:
    def __init__(self) -> None:
        self.inner, self.probe, self.clock = ScriptedDirectory(), ScriptedProbe(), FakeClock()
        self.caching = CachingAgentDirectory(self.inner, self.probe, self.clock)

    def now_ns(self) -> int:
        return int(self.clock.time() * 1e9)

    def quiet(self, addr: str, seconds: float = 60.0) -> None:
        """The directory of ``addr`` was last modified ``seconds`` ago."""
        self.probe.mtimes[(addr, "")] = self.now_ns() - int(seconds * SECOND)


def test_it_is_an_agent_directory() -> None:
    assert isinstance(Setup().caching, AgentDirectory)


def test_building_it_asks_nothing() -> None:
    s = Setup()
    assert s.inner.listed == [] and s.probe.asked == []


def test_a_quiet_directory_is_listed_once() -> None:
    s = Setup()
    s.quiet("root")
    first = s.caching.children("root")
    assert first == ["a", "b"] and s.caching.children("root") is first
    assert s.inner.listed == ["root"]


def test_the_directory_is_asked_for_with_the_normalized_address_and_the_empty_name() -> None:
    s = Setup()
    s.quiet("a")
    s.caching.children(" /a/ ")
    assert s.probe.asked == [("a", "")] and s.inner.listed == ["a"]
    s.caching.children("a")
    assert s.probe.asked == [("a", ""), ("a", "")] and s.inner.listed == ["a"]


def test_a_directory_that_changed_is_listed_again() -> None:
    s = Setup()
    s.quiet("root", 60)
    assert s.caching.children("root") == ["a", "b"]
    s.inner.kids["root"] = ["a", "b", "c"]
    assert s.caching.children("root") == ["a", "b"]  # nothing told the cache
    s.quiet("root", 30)
    assert s.caching.children("root") == ["a", "b", "c"] and s.inner.listed == ["root", "root"]


def test_a_directory_modified_just_before_it_was_listed_is_not_trusted() -> None:
    s = Setup()
    s.quiet("root", 0.5)
    s.caching.children("root")
    s.inner.kids["root"] = ["a"]
    s.clock.advance(60)  # the directory has been quiet since, but the mtime is the same: it could have changed again within the tick
    assert s.caching.children("root") == ["a"] and s.inner.listed == ["root", "root"]


def test_the_trust_window_is_two_seconds_and_a_directory_exactly_that_old_is_not_trusted() -> None:
    assert CACHE_TRUST == 2.0
    s = Setup()
    s.quiet("root", 2.0)
    s.caching.children("root")
    s.caching.children("root")
    assert s.inner.listed == ["root", "root"]
    s2 = Setup()
    s2.quiet("root", 2.001)
    s2.caching.children("root")
    s2.caching.children("root")
    assert s2.inner.listed == ["root"]


def test_a_missing_directory_has_no_children_and_the_inner_directory_is_not_asked() -> None:
    s = Setup()
    assert s.caching.children("nobody") == [] and s.inner.listed == []


def test_a_directory_that_vanished_has_no_children_whatever_was_cached() -> None:
    s = Setup()
    s.quiet("root")
    assert s.caching.children("root") == ["a", "b"]
    del s.probe.mtimes[("root", "")]
    assert s.caching.children("root") == []


def test_every_address_has_its_own_entry() -> None:
    s = Setup()
    s.quiet("root")
    s.quiet("a")
    assert (s.caching.children("root"), s.caching.children("a")) == (["a", "b"], ["a/x"])
    s.caching.children("root")
    s.caching.children("a")
    assert s.inner.listed == ["root", "a"]


def test_agents_and_subtree_walk_over_the_cached_children() -> None:
    s = Setup()
    for addr in ("root", "a", "b", "a/x"):
        s.quiet(addr)
    assert s.caching.agents() == ["a", "a/x", "b"]
    assert s.caching.subtree("root") == ["root", "b", "a", "a/x"]
    assert s.caching.agents() == ["a", "a/x", "b"]
    assert sorted(s.inner.listed) == ["a", "a/x", "b", "root"]  # each directory listed once, however often it was walked


def test_exists_and_require_are_the_inner_ones() -> None:
    s = Setup()
    assert s.caching.exists("a/x") is True and s.caching.exists("zz") is False
    assert s.caching.require(" /a/ ") == "a"
    with pytest.raises(OrgError, match="no such agent: zz"):
        s.caching.require("zz")
    assert s.inner.listed == []
