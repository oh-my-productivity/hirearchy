"""``EnvBindingResolver``: the matrix of ``ORG_AGENT`` / ``ORG_REQUIRE_AGENT`` / ``ORG_ROOT`` and the way it fails closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import ROOT, OrgError
from orgmcp.kernel.testing import DictEnvironment
from orgmcp.locator.testing import MemoryOrgLocator
from orgmcp.mcp_server._binding import OpenerBindings
from orgmcp.mcp_server._resolver import EnvBindingResolver
from orgmcp.mcp_server.testing import MemoryOrgOpener


REFUSAL = (
    "ORG_REQUIRE_AGENT is set but ORG_AGENT does not name an agent: this is an internal profile of the "
    "orgmcp scheduler and only works when the scheduler starts it. Refusing to act as root. "
    "To manage an organization yourself, register `orgmcp mcp` without ORG_REQUIRE_AGENT")


def resolver(tmp_path: Path, variables: dict[str, str], exists: bool = True) -> tuple[EnvBindingResolver, MemoryOrgOpener]:
    root = tmp_path / "org"
    environment = DictEnvironment({"ORG_ROOT": str(root), **variables}, cwd=tmp_path / "cwd")
    opener = MemoryOrgOpener({root} if exists else set())
    locator = MemoryOrgLocator(environment, {root} if exists else set())
    return EnvBindingResolver(environment, locator, opener, OpenerBindings(opener)), opener


@pytest.mark.parametrize("require", ["1", "true", "yes", "on", "anything", " 1 "])
@pytest.mark.parametrize("agent", [None, "", "  ", "root", " root ", "/"])
def test_a_required_agent_that_is_not_one_refuses_to_start(tmp_path: Path, require: str, agent: str | None) -> None:
    variables = {"ORG_REQUIRE_AGENT": require} | ({"ORG_AGENT": agent} if agent is not None else {})
    with pytest.raises(OrgError) as info:
        resolver(tmp_path, variables)[0].resolve()
    assert str(info.value) == REFUSAL


@pytest.mark.parametrize("off", ["", "0", "false", "no", "FALSE", "No", "  "])
def test_a_requirement_that_is_off_is_off(tmp_path: Path, off: str) -> None:
    binding, me = resolver(tmp_path, {"ORG_REQUIRE_AGENT": off})[0].resolve()
    assert me == ROOT and binding.root == tmp_path / "org"


def test_a_required_agent_that_is_one_is_served(tmp_path: Path) -> None:
    binding, me = resolver(tmp_path, {"ORG_REQUIRE_AGENT": "1", "ORG_AGENT": "ceo/eng"})[0].resolve()
    assert me == "ceo/eng" and binding.pinned and binding.location() == tmp_path / "org"


def test_the_agent_is_named_by_the_stripped_variable(tmp_path: Path) -> None:
    assert resolver(tmp_path, {"ORG_AGENT": "  ceo "})[0].resolve()[1] == "ceo"


def test_an_agent_without_its_organization_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(OrgError):
        resolver(tmp_path, {"ORG_AGENT": "ceo"}, exists=False)[0].resolve()


def test_root_is_bound_to_the_path_whether_or_not_an_organization_is_there(tmp_path: Path) -> None:
    binding, me = resolver(tmp_path, {}, exists=False)[0].resolve()
    assert me == ROOT and binding.root == tmp_path / "org" and binding.peek() is None
    assert binding.pinned  # bound by ORG_ROOT: create_org may not choose another path


def test_root_without_any_organization_is_unbound_and_not_pinned(tmp_path: Path) -> None:
    environment = DictEnvironment({}, cwd=tmp_path)
    opener = MemoryOrgOpener()
    binding, me = EnvBindingResolver(environment, MemoryOrgLocator(environment), opener, OpenerBindings(opener)).resolve()
    assert me == ROOT and binding.root is None and not binding.pinned


def test_an_empty_org_root_does_not_pin(tmp_path: Path) -> None:
    binding, _ = resolver(tmp_path, {"ORG_ROOT": ""}, exists=False)[0].resolve()
    assert not binding.pinned
